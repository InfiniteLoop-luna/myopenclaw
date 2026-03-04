"""
convert.py - DDM 到 OSM 转换主脚本

使用方法:
    python convert.py <ddm_file> <output_yaml> [database_name]

示例:
    python convert.py sakila.ddm sakila_osm.yaml sakila
"""
import sys
import os
import io
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加 scripts 目录到 path（使用 Path 处理跨平台路径）
script_dir = Path(__file__).parent / 'scripts'
sys.path.insert(0, str(script_dir))

from ddm_parser import DDMParser
from osm_generator import OSMGenerator


def convert_ddm_to_osm(ddm_file: str, output_file: str, database_name: str = "database"):
    """
    将 DDM 文件转换为 OSM YAML
    
    Args:
        ddm_file: DDM 文件路径
        output_file: 输出的 OSM YAML 文件路径
        database_name: 数据库名称
    """
    # 检查输入文件是否存在
    if not os.path.exists(ddm_file):
        print(f"❌ 错误: DDM 文件不存在: {ddm_file}")
        print(f"\n请检查:")
        print(f"  1. 文件路径是否正确")
        print(f"  2. 文件是否存在")
        print(f"  3. 是否有读取权限")
        sys.exit(1)
    
    print(f"📖 解析 DDM 文件: {ddm_file}")
    
    try:
        parser = DDMParser(ddm_file)
        entities = parser.parse()
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        print(f"\n请检查:")
        print(f"  1. DDM 文件格式是否正确（应为 XML 格式）")
        print(f"  2. 文件是否是 Datablau LDM 格式")
        print(f"  3. 文件编码是否为 UTF-8")
        print(f"\n查看 docs/TROUBLESHOOTING.md 获取更多帮助")
        sys.exit(1)
    
    print(f"✅ 解析到 {len(entities)} 个实体")
    
    # 显示实体列表
    print("\n实体列表:")
    for entity_name, entity in entities.items():
        print(f"  - {entity_name} ({entity.label}): {len(entity.attributes)} 个属性, {len(entity.foreign_keys)} 个外键")
    
    print(f"\n🔨 生成 OSM 模型...")
    try:
        generator = OSMGenerator(entities, database_name)
        osm = generator.generate()
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        print(f"\n查看 docs/TROUBLESHOOTING.md 获取帮助")
        sys.exit(1)
    
    print(f"✅ 生成完成:")
    print(f"  - Ontology 实体: {len(osm['ontology']['entities'])}")
    print(f"  - Semantic Models: {len(osm['semantic_models'])}")
    print(f"  - Join Graph 边: {len(osm['join_graph']['edges'])}")
    print(f"  - KPIs: {len(osm['kpis'])}")
    
    print(f"\n💾 保存到: {output_file}")
    try:
        generator.save_yaml(output_file)
    except Exception as e:
        print(f"❌ 保存失败: {e}")
        print(f"\n请检查:")
        print(f"  1. 是否有写入权限")
        print(f"  2. 磁盘空间是否充足")
        print(f"  3. 文件是否被其他程序占用")
        sys.exit(1)
    
    print(f"\n✨ 转换完成！")
    print(f"\n下一步:")
    print(f"  1. 检查生成的 {output_file} 文件")
    print(f"  2. 根据业务需求调整 KPI 定义")
    print(f"  3. 添加更多的业务规则到 Governance Layer")
    print(f"  4. 使用 OSM 编译器测试查询")


def main():
    if len(sys.argv) < 3:
        print("DDM 到 OSM 转换工具")
        print("\n使用方法:")
        print("  python convert.py <ddm_file> <output_yaml> [database_name]")
        print("\n示例:")
        print("  python convert.py sakila.ddm sakila_osm.yaml sakila")
        print("\n参数说明:")
        print("  ddm_file       - DDM 文件路径 (.ddm)")
        print("  output_yaml    - 输出的 OSM YAML 文件路径")
        print("  database_name  - 数据库名称 (可选，默认为 'database')")
        sys.exit(1)
    
    ddm_file = sys.argv[1]
    output_file = sys.argv[2]
    database_name = sys.argv[3] if len(sys.argv) > 3 else "database"
    
    convert_ddm_to_osm(ddm_file, output_file, database_name)


if __name__ == "__main__":
    main()
