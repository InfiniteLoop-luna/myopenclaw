"""
测试 ddm-to-osm skill 是否正常工作
"""
import os
import sys
import io
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_skill():
    """运行所有测试"""
    print("🧪 测试 ddm-to-osm skill\n")
    
    all_passed = True
    
    # 测试 1: 检查 Python 版本
    print("1️⃣ 检查 Python 版本...")
    if sys.version_info < (3, 7):
        print(f"   ❌ Python 版本过低: {sys.version}")
        print(f"   需要 Python 3.7 或更高版本")
        all_passed = False
    else:
        print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # 测试 2: 检查依赖
    print("\n2️⃣ 检查依赖...")
    try:
        import yaml
        print("   ✅ PyYAML 已安装")
    except ImportError:
        print("   ❌ PyYAML 未安装")
        print("   运行: pip install pyyaml")
        all_passed = False
    
    # 测试 3: 检查文件结构
    print("\n3️⃣ 检查文件结构...")
    required_files = [
        'convert.py',
        'scripts/ddm_parser.py',
        'scripts/osm_generator.py',
        'SKILL.md',
        'README.md',
        'skill.json',
        'LICENSE',
        'CHANGELOG.md',
        'requirements.txt'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"   ❌ 缺少文件: {file}")
            all_passed = False
        else:
            print(f"   ✅ {file}")
    
    # 测试 4: 检查文档
    print("\n4️⃣ 检查文档...")
    doc_files = [
        'docs/OSM_CONCEPTS.md',
        'docs/DDM_FORMAT.md',
        'docs/TROUBLESHOOTING.md'
    ]
    
    for file in doc_files:
        if not os.path.exists(file):
            print(f"   ❌ 缺少文档: {file}")
            all_passed = False
        else:
            print(f"   ✅ {file}")
    
    # 测试 5: 测试导入
    print("\n5️⃣ 测试模块导入...")
    try:
        sys.path.insert(0, 'scripts')
        from ddm_parser import DDMParser
        from osm_generator import OSMGenerator
        print("   ✅ ddm_parser 导入成功")
        print("   ✅ osm_generator 导入成功")
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        all_passed = False
    
    # 测试 6: 测试示例文件（如果存在）
    print("\n6️⃣ 测试示例转换...")
    if os.path.exists('examples/sample.ddm'):
        try:
            print("   运行: python convert.py examples/sample.ddm test_output.yaml test_db")
            result = os.system('python convert.py examples/sample.ddm test_output.yaml test_db')
            if result == 0 and os.path.exists('test_output.yaml'):
                print("   ✅ 转换成功")
                # 清理测试文件
                os.remove('test_output.yaml')
            else:
                print("   ❌ 转换失败")
                all_passed = False
        except Exception as e:
            print(f"   ❌ 转换出错: {e}")
            all_passed = False
    else:
        print("   ⚠️  未找到示例文件 examples/sample.ddm")
        print("   跳过转换测试")
    
    # 总结
    print("\n" + "="*50)
    if all_passed:
        print("✨ 所有测试通过！")
        print("\n使用方法:")
        print("  python convert.py <ddm_file> <output_yaml> [database_name]")
        print("\n示例:")
        print("  python convert.py sakila.ddm sakila_osm.yaml sakila")
        return 0
    else:
        print("❌ 部分测试失败")
        print("\n请查看上面的错误信息并修复")
        print("或查看 docs/TROUBLESHOOTING.md 获取帮助")
        return 1

if __name__ == "__main__":
    sys.exit(test_skill())
