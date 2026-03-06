# DDM to OSM Converter - 使用示例

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 转换 DDM 到 OSM（advanced，默认）
python convert.py path/to/your.ddm output.yaml database_name

# 3. 仅基础 KPI（basic）
python convert.py path/to/your.ddm output_basic.yaml database_name --kpi-mode basic

# 4. 使用 profile 配置数据源
python convert.py path/to/your.ddm output_profiled.yaml database_name --profile profile.example.yaml
```

## 输出日志示例

```text
📖 解析 DDM 文件: sakila.ddm
✅ 解析到 17 个实体

🔨 生成 OSM 模型...
✅ 生成完成:
  - Ontology 实体: 17
  - Semantic Models: 17
  - Join Graph 边: 21
  - KPIs: 70
  - KPI 模式: basic

💾 保存到: sakila_generated_basic.yaml
✨ 转换完成！
```

## 生成的 OSM 结构（P0）

### 1) meta

```yaml
meta:
  schema_version: osm-v1.0
  generator: ddm-to-osm
  generator_version: 1.1.0-p0
  generated_at: 2026-03-06T...
  kpi_mode: basic
  source:
    ddm: sakila.ddm
    database: sakila
```

### 2) Ontology Layer（语义真相层）

```yaml
ontology:
  entities:
    Address:
      label: 地址表
      description: 地址表
      attributes:
        city_id:
          label: 城市ID
          type: integer
          nullable: false
          semantic_type: foreign_key
      relations:
        - name: city-address
          target: City
          cardinality: many_to_one
          inverse: addresses
```

### 3) Semantic Model Layer（数据映射层）

```yaml
semantic_models:
  address:
    entity: Address
    data_source:
      type: mysql
      connection: sakila
    table: address
    primary_key: address_id
    joins:
      city_address_join:
        target_model: city
        relationship: many_to_one
        join_type: left
        condition:
          type: key
          local_key: city_id
          foreign_key: city_id
        required: false
```

> 复合外键时，condition 会自动输出 `local_keys/foreign_keys`。

### 4) KPI Layer（time 结构统一）

```yaml
kpis:
  address_count:
    computation:
      type: aggregation
      base_model: address
      aggregation: count
    time:
      dimension: last_update
      default_grain: month
      allowed_grains: [day, week, month, quarter, year]
      window: null
```

## 验证与回归

```bash
python test.py
```

测试包含：
- parser/generator 导入
- sakila golden 回归（17 entities / 21 join edges）
- KPI time 结构一致性
- semantic_type 与 inverse 命名回归

## 下一步

1. 检查生成 YAML 的实体与关系
2. 根据业务筛选 KPI（basic/advanced）
3. 按治理需求补充规则与权限

## 参考

- [OSM 概念说明](docs/OSM_CONCEPTS.md)
- [DDM 格式说明](docs/DDM_FORMAT.md)
- [故障排除](docs/TROUBLESHOOTING.md)
