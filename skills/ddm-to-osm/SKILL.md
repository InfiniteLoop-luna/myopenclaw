# DDM to OSM Converter Skill

自动将 Datablau DDM (Data Definition Model) 文件转换为 OSM (Ontology-Lite Semantic Model) YAML 格式。

## 功能

从 DDM 文件中提取数据库模型信息，自动生成包含四层结构的 OSM 模型：

1. **Ontology Layer（语义真相层）**：实体、属性、关系定义
2. **Semantic Model Layer（数据映射层）**：数据源映射、维度、度量、Join 定义
3. **KPI Layer（业务指标层）**：基础 KPI 定义
4. **Governance Layer（治理层）**：规则和权限策略

## 使用方法

### 基础用法

```bash
python convert.py <ddm_file> <output_yaml> [database_name]
```

### 参数说明

- `ddm_file` - DDM 文件路径（.ddm 格式）
- `output_yaml` - 输出的 OSM YAML 文件路径
- `database_name` - 数据库名称（可选，默认为 "database"）

### 示例

```bash
# 转换 sakila 数据库模型
python convert.py sakila.ddm sakila_osm.yaml sakila

# 转换其他数据库模型
python convert.py ecommerce.ddm ecommerce_osm.yaml ecommerce
```

## 转换内容

### 1. Ontology Layer

从 DDM 的 EntityComposite 和 EntityAttribute 生成：

- **实体（Entity）**：从 DDM 的表定义生成，包含中文标签
- **属性（Attribute）**：包含类型映射、可空性、默认值等
- **关系（Relation）**：从外键关系推断实体间的关联
- **语义类型推断**：自动识别 identifier、name、email、currency 等语义类型

### 2. Semantic Model Layer

为每个实体生成：

- **数据源配置**：数据库类型、连接信息、表名
- **主键定义**：从 DDM 的 PrimaryKey 提取
- **维度（Dimensions）**：非数值字段作为维度
- **度量（Measures）**：数值字段作为度量，默认聚合方式为 sum
- **Join 定义**：从外键关系生成 join 配置

### 3. Join Graph

自动构建：

- **节点（Nodes）**：所有 semantic models
- **边（Edges）**：基于外键关系的 join 路径

### 4. KPI Layer

为每个实体生成基础 KPI：

- **Count KPI**：统计实体数量
- **时间维度**：自动识别时间字段（包含 date/time 的字段）
- **时间粒度**：支持 day、week、month、year

### 5. Governance Layer

生成基础治理规则：

- **规则（Rules）**：时间维度强制要求等
- **权限策略（Policies）**：admin 和 analyst 角色的基础权限

## 输出示例

生成的 OSM YAML 文件结构：

```yaml
# ============================================================
# OSM (Ontology-Lite Semantic Model)
# Auto-generated from DDM
# Database: sakila
# ============================================================

ontology:
  entities:
    Actor:
      label: 演员信息表
      description: 演员信息表
      attributes:
        actor_id:
          label: 演员ID
          type: integer
          physical_type: SMALLINT UNSIGNED
          nullable: false
          semantic_type: identifier
          auto_increment: true
        first_name:
          label: 演员名字
          type: string
          physical_type: VARCHAR(45)
          nullable: false
          semantic_type: name
      relations:
        - name: film_actor_fk
          target: Film
          cardinality: many_to_one
          inverse: actors

semantic_models:
  actor:
    entity: Actor
    data_source:
      type: mysql
      connection: sakila
    table: actor
    primary_key: actor_id
    dimensions:
      actor_id:
        label: 演员ID
        column: actor_id
        type: integer
      first_name:
        label: 演员名字
        column: first_name
        type: string
    measures: {}
    joins: {}

join_graph:
  nodes:
    - actor
    - film
    - ...
  edges:
    - from: film_actor
      to: actor
      join_id: actor_join

kpis:
  actor_count:
    name: 演员信息表数量
    description: 统计演员信息表的数量
    host:
      entity: Actor
      cardinality: many
      grain: entity
    computation:
      type: aggregation
      base_model: actor
      measure: count
      aggregation: count
    time:
      dimension: last_update
      grain: [day, week, month, year]
      default_grain: month

governance:
  rules:
    - id: require_time_dimension
      condition: kpi.time.dimension is not None
      action: enforce_time_dimension
  policies:
    role_permissions:
      admin:
        allowed_kpis: ['*']
        allowed_entities: ['*']
```

## 后续步骤

生成 OSM 文件后，你需要：

1. **检查生成的文件**：确认实体、属性、关系是否正确
2. **调整 KPI 定义**：根据业务需求添加更多有意义的 KPI
3. **完善关系定义**：检查并调整实体间的关系（many_to_one、one_to_many 等）
4. **添加业务规则**：在 Governance Layer 添加更多的业务约束
5. **测试查询**：使用 OSM 编译器测试 IR 到 SQL 的转换

## 类型映射

DDM 物理类型到 OSM 语义类型的映射：

| DDM 物理类型 | OSM 语义类型 |
|-------------|-------------|
| INT, SMALLINT, BIGINT, TINYINT | integer |
| DECIMAL, NUMERIC, FLOAT, DOUBLE | decimal |
| VARCHAR, CHAR, TEXT | string |
| DATE, DATETIME, TIMESTAMP | datetime |
| BOOLEAN, BOOL | boolean |
| GEOMETRY, POINT | geometry |

## 语义类型推断

根据字段名自动推断语义类型：

| 字段名模式 | 语义类型 |
|-----------|---------|
| *_id (主键) | identifier |
| *_id (外键) | foreign_key |
| *name*, *title* | name |
| *email* | email |
| *phone*, *tel* | phone |
| *date*, *time* | timestamp |
| *amount*, *price*, *cost* | currency |
| *rate*, *percent* | percentage |
| *status*, *state* | status |
| *count*, *number* | count |

## 依赖

- Python 3.7+
- PyYAML

安装依赖：

```bash
pip install pyyaml
```

## 文件结构

```
ddm-to-osm/
├── SKILL.md              # 本文档
├── convert.py            # 主转换脚本
└── scripts/
    ├── ddm_parser.py     # DDM XML 解析器
    └── osm_generator.py  # OSM YAML 生成器
```

## 限制

1. **关系推断**：目前主要基于外键关系推断，复杂的多对多关系可能需要手动调整
2. **KPI 生成**：只生成基础的 count KPI，业务 KPI 需要手动添加
3. **语义类型**：基于字段名的启发式推断，可能需要手动调整
4. **Join 类型**：默认生成 left join，可能需要根据业务调整为 inner join

## 故障排除

### 问题：解析 DDM 文件失败

- 确认 DDM 文件格式正确（XML 格式）
- 检查文件编码是否为 UTF-8
- 确认 DDM 文件是 Datablau LDM 格式

### 问题：生成的关系不正确

- 检查 DDM 文件中的外键定义
- 手动调整生成的 OSM YAML 中的 relations 部分

### 问题：缺少某些实体

- 确认 DDM 文件中包含这些实体
- 检查实体是否有 EntityComposite 类型定义

## 示例：完整工作流

```bash
# 1. 转换 DDM 到 OSM
python convert.py sakila.ddm sakila_osm.yaml sakila

# 2. 检查生成的文件
cat sakila_osm.yaml

# 3. 手动调整 KPI 定义（使用编辑器）
# 添加业务相关的 KPI，如：
# - store_revenue: 门店收入
# - customer_lifetime_value: 客户生命周期价值
# - film_rental_count: 电影租赁次数

# 4. 使用 OSM 编译器测试
cd ../sakila_osm/compiler
python demo.py
```

## 相关资源

- [OSM 概念说明](docs/OSM_CONCEPTS.md) - 本地文档，详细介绍 OSM 四层架构
- [DDM 格式说明](docs/DDM_FORMAT.md) - DDM XML 格式详解
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题和解决方案
- [使用示例](EXAMPLE.md) - 详细的使用示例和输出示例
