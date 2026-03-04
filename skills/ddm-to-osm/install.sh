#!/bin/bash
# ddm-to-osm skill 安装脚本 (Linux/Mac)

echo "📦 安装 ddm-to-osm skill..."
echo ""

# 检查 Python 版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 安装依赖
echo ""
echo "安装依赖..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ddm-to-osm skill 安装成功！"
    echo ""
    echo "运行测试:"
    echo "  python3 test.py"
    echo ""
    echo "使用方法:"
    echo "  python3 convert.py <ddm_file> <output_yaml> [database_name]"
    echo ""
    echo "示例:"
    echo "  python3 convert.py sakila.ddm sakila_osm.yaml sakila"
else
    echo ""
    echo "❌ 安装失败"
    echo "请检查错误信息或查看 docs/TROUBLESHOOTING.md"
    exit 1
fi
