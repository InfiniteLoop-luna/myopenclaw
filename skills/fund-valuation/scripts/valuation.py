#!/usr/bin/env python3
"""
基金实时估值计算工具

根据基金最新季报持仓和股票实时行情，估算基金当日净值。
"""

import sys
import json
import re
from urllib.request import urlopen, Request
from urllib.parse import quote
from html import unescape


def fetch_url(url, timeout=10):
    """获取URL内容"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            raw_data = response.read()
            
            # 尝试多种编码
            for enc in ['utf-8', 'gb18030', 'gbk', 'gb2312']:
                try:
                    return raw_data.decode(enc)
                except:
                    continue
            
            # 如果都失败，使用utf-8并忽略错误
            return raw_data.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def search_fund_code(keyword):
    """搜索基金代码"""
    url = f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={quote(keyword)}"
    content = fetch_url(url)
    if not content:
        return None
    
    try:
        data = json.loads(content)
        if data.get('Datas') and len(data['Datas']) > 0:
            # 返回第一个匹配结果
            fund = data['Datas'][0]
            return {
                'code': fund['CODE'],
                'name': fund['NAME'],
                'type': fund['TYPE']
            }
    except:
        pass
    
    return None


def get_fund_holdings(fund_code):
    """获取基金持仓数据"""
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
    content = fetch_url(url)
    if not content:
        return None
    
    # 解析JavaScript变量
    match = re.search(r'var apidata=\s*\{\s*content:"(.*?)",arryear', content, re.DOTALL)
    if not match:
        return None
    
    try:
        # 获取HTML内容（已转义）
        html_content = match.group(1)
        # 解码转义字符
        html_content = html_content.replace('\\n', '\n').replace('\\/', '/')
        
        # 提取持仓数据
        # 匹配模式：<td>序号</td><td>代码链接</td><td>名称链接</td>...后面有占比
        pattern = r"<td>(\d+)</td><td><a[^>]*>(\d+)</a></td><td[^>]*><a[^>]*>([^<]+)</a></td>.*?(\d+\.\d+)%"
        matches = re.findall(pattern, html_content, re.DOTALL)
        
        holdings = []
        for match in matches[:10]:  # 只取前10个
            seq, code, name, ratio = match
            holdings.append({
                'code': code,
                'name': name.strip(),
                'ratio': float(ratio)
            })
        
        if holdings:
            return holdings
        
    except Exception as e:
        print(f"Error parsing holdings: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    
    return None


def get_stock_quotes(stock_codes):
    """获取股票实时行情"""
    # 构建secids参数
    secids = []
    for code in stock_codes:
        if code.startswith('6'):
            secids.append(f'1.{code}')  # 上海
        elif code.startswith('0') or code.startswith('3'):
            secids.append(f'0.{code}')  # 深圳
        elif code.startswith('688') or code.startswith('689'):
            secids.append(f'1.{code}')  # 科创板
        else:
            secids.append(f'0.{code}')  # 默认深圳
    
    secids_str = ','.join(secids)
    url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f12,f14&secids={secids_str}"
    
    content = fetch_url(url)
    if not content:
        return None
    
    try:
        data = json.loads(content)
        quotes = {}
        for item in data['data']['diff']:
            quotes[item['f12']] = {
                'name': item['f14'],
                'price': item['f2'],
                'change': item['f3']
            }
        return quotes
    except Exception as e:
        print(f"Error parsing quotes: {e}", file=sys.stderr)
    
    return None


def calculate_valuation(holdings, quotes):
    """计算估值"""
    total_contribution = 0.0
    total_ratio = 0.0
    
    results = []
    for holding in holdings:
        code = holding['code']
        name = holding['name']
        ratio = holding['ratio']
        
        if code in quotes:
            quote = quotes[code]
            change = quote['change']
            contribution = ratio * change / 100
            total_contribution += contribution
            total_ratio += ratio
            
            results.append({
                'code': code,
                'name': name,
                'ratio': ratio,
                'change': change,
                'contribution': contribution
            })
    
    return {
        'holdings': results,
        'total_ratio': total_ratio,
        'estimated_change': total_contribution
    }


def format_output(fund_info, valuation):
    """格式化输出"""
    print(f"\n{'='*60}")
    print(f"基金名称: {fund_info['name']}")
    print(f"基金代码: {fund_info['code']}")
    print(f"{'='*60}\n")
    
    print(f"{'股票代码':<10} {'股票名称':<12} {'持仓占比':<10} {'今日涨跌':<10} {'贡献估值':<10}")
    print(f"{'-'*60}")
    
    for h in valuation['holdings']:
        print(f"{h['code']:<10} {h['name']:<12} {h['ratio']:>6.2f}% {h['change']:>8.2f}% {h['contribution']:>8.2f}%")
    
    print(f"{'-'*60}")
    print(f"前{len(valuation['holdings'])}大重仓股合计占比: {valuation['total_ratio']:.2f}%")
    print(f"\n估算今日涨跌: {valuation['estimated_change']:+.2f}%")
    print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("用法: python valuation.py <基金代码或名称>")
        print("示例: python valuation.py 007491")
        print("示例: python valuation.py 南方信息创新")
        return 1
    
    keyword = sys.argv[1]
    
    # 判断是代码还是名称
    if keyword.isdigit() and len(keyword) == 6:
        fund_code = keyword
        fund_info = {'code': fund_code, 'name': ''}
    else:
        print(f"搜索基金: {keyword}...")
        fund_info = search_fund_code(keyword)
        if not fund_info:
            print(f"未找到基金: {keyword}", file=sys.stderr)
            return 1
        fund_code = fund_info['code']
        print(f"找到基金: {fund_info['name']} ({fund_code})\n")
    
    # 获取持仓
    print("获取持仓数据...")
    holdings = get_fund_holdings(fund_code)
    if not holdings:
        print("无法获取持仓数据", file=sys.stderr)
        return 1
    
    print(f"获取到 {len(holdings)} 只重仓股\n")
    
    # 获取行情
    print("获取实时行情...")
    stock_codes = [h['code'] for h in holdings]
    quotes = get_stock_quotes(stock_codes)
    if not quotes:
        print("无法获取行情数据", file=sys.stderr)
        return 1
    
    # 计算估值
    valuation = calculate_valuation(holdings, quotes)
    
    # 输出结果
    format_output(fund_info, valuation)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
