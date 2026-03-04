# DDM to OSM Converter

✅ **Skill 创建完成！**

## 功能

自动将 Datablau DDM (Data Definition Model) 文件转换为 OSM (Ontology-Lite Semantic Model) YAML 格式。

## 文件结构

```
ddm-to-osm/
├── SKILL.md              # 详细使用文档
├── EXAMPLE.md            # 使用示例和输出示例
├── convert.py            # 主转换脚本
├── requirements.txt      # 依赖项 (pyyaml)
└── scripts/
    ├── ddm_parser.py     # DDM XML 解析器
    └── osm_generator.py  # OSM YAML 生成器
```

## 快速使用

```bash
# 安装依赖
pip install pyyaml

# 转换 DDM 到 OSM
python convert.py <ddm_file> <output_yaml> [database_name]

# 示例
python convert.py sakila.ddm sakila_osm.yaml sakila
```

## 转换内容

✅ **Ontology Layer** - 实体、属性、关系定义  
✅ **Semantic Model Layer** - 数据源映射、维度、度量、Join 定义  
✅ **Join Graph** - 自动构建实体间的连接图  
✅ **KPI Layer** - 为每个实体生成基础 count KPI  
✅ **Governance Layer** - 基础规则和权限策略  

## 测试结果

使用 sakila.ddm 测试：
- ✅ 解析 17 个实体
- ✅ 识别 21 个外键关系
- ✅ 生成 21 条 Join Graph 边
- ✅ 生成 15 个基础 KPI
- ✅ 正确推断语义类型（identifier, name, email, phone, currency 等）

## 特性

- 🔍 **智能解析**：自动识别实体、属性、主键、外键、索引
- 🧠 **语义推断**：根据字段名自动推断语义类型
- 🔗 **关系识别**：自动解析 RelationshipRelational 并生成 Join 定义
- 📊 **类型映射**：DDM 物理类型到 OSM 语义类型的智能映射
- 🌐 **中文支持**：完整支持中文标签和描述
- ⚡ **快速生成**：秒级完成大型数据库模型的转换

## 下一步

生成 OSM 后，你可以：
1. 手动调整和完善 KPI 定义
2. 添加更多业务规则到 Governance Layer
3. 使用 OSM 编译器测试 IR 到 SQL 的转换
4. 集成到你的语义数据平台

## 相关资源

- [OSM 概念说明](docs/OSM_CONCEPTS.md) - 本地文档，详细介绍 OSM 四层架构
- [DDM 格式说明](docs/DDM_FORMAT.md) - DDM XML 格式详解
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题和解决方案
- [使用示例](EXAMPLE.md) - 详细的使用示例和输出示例

---

**Created**: 2026-03-03  
**Version**: 1.0  
**Status**: ✅ Ready to use
