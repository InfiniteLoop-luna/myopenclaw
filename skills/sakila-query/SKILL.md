---
name: sakila-query
description: "Sakila DVD 租赁数据库的自然语言查询。将用户的中文/英文数据问题转为 IR JSON，通过 OSM 语义编译器生成 SQL 并执行。Use when: 用户询问门店收入、租赁数据、客户分析、电影排行、员工业绩等 Sakila 数据库相关的业务问题。NOT for: 非数据查询的一般对话、修改数据库结构、直接写 SQL。"
---

# Sakila 语义查询

通过 OSM 语义编译器将自然语言转为 SQL 查询 Sakila DVD 租赁数据库。

## 流程

1. 理解用户意图，参考 `references/semantic-metadata.md` 确定 KPI、实体、时间、过滤条件
2. 构造 IR JSON
3. 调用 `scripts/query.py` 编译为 SQL
4. 执行 SQL（如有数据库连接）
5. 用自然语言解释结果

## 注意

- Sakila 数据时间范围: 2005-05 ~ 2006-02，使用 absolute 时间范围而非 relative
- 默认时间范围建议: `{"type": "absolute", "value": "2005-05-01/2006-03-01"}`
- 执行环境变量: `PYTHONIOENCODING=utf-8`

## 第 1 步：意图 → IR 映射

读取 `references/semantic-metadata.md` 获取可用 KPI 列表和 IR 结构。

映射规则：
- "收入/营收/revenue" → store_revenue 或 total_revenue
- "增长率/同比" → revenue_growth
- "租赁/借片" → total_rentals
- "客户/顾客" → active_customers 或 customer_lifetime_value
- "电影排行/热门电影" → film_rental_count + ranking
- "分类收入" → category_revenue
- "员工业绩" → staff_revenue 或 staff_rental_count
- "平均租赁时长" → avg_rental_duration
- "逾期" → overdue_rentals
- "库存利用率" → inventory_utilization
- "客均收入" → revenue_per_customer

时间映射：
- "最近一年/过去12个月" → last_12_months
- "最近一个月/上个月" → last_30_days
- "今年" → ytd
- "本月" → mtd
- 具体日期 → absolute 格式 "YYYY-MM-DD/YYYY-MM-DD"

## 第 2 步：编译 IR

```bash
python <skill_dir>/scripts/query.py '<IR_JSON>'
```

设置环境变量 `PYTHONIOENCODING=utf-8`。

如果编译失败，检查错误信息并修正 IR（常见：缺少 time、非法 filter、权限不足）。

## 第 3 步：执行 SQL

编译成功后拿到 SQL，如果用户配置了数据库连接，直接执行。否则展示 SQL 让用户自行执行。

数据库连接信息在 TOOLS.md 中查找（如有配置）。

## 第 4 步：解释结果

用自然语言总结查询结果，包括：
- 关键数字和趋势
- 对比分析（如有多个维度）
- 简短的业务洞察

## 示例

用户: "各门店最近一年每月收入是多少？"

IR:
```json
{
  "kpi": "store_revenue",
  "host": {"entity": "Store"},
  "time": {"grain": "month", "range": {"type": "relative", "value": "last_12_months"}}
}
```

用户: "哪些电影最受欢迎？给我 Top 10"

IR:
```json
{
  "kpi": "film_rental_count",
  "host": {"entity": "Film"},
  "ranking": {"order_by": "film_rental_count", "limit": 10, "direction": "desc"}
}
```

用户: "1号门店 Alberta 地区的收入"

IR:
```json
{
  "kpi": "store_revenue",
  "host": {"entity": "Store", "ids": [1]},
  "time": {"grain": "month", "range": {"type": "relative", "value": "last_12_months"}},
  "filters": [{"field": "district", "operator": "=", "value": "Alberta"}]
}
```
