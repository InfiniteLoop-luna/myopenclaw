# DDM to OSM Converter - 使用示例

## 快速开始

```bash
# 1. 安装依赖
pip install pyyaml

# 2. 转换 DDM 到 OSM
python convert.py path/to/your.ddm output.yaml database_name

# 示例：转换 sakila 数据库
python convert.py ../sakila_osm/sakila.ddm sakila_generated.yaml sakila
```

## 输出示例

转换成功后，你会看到：

```
📖 解析 DDM 文件: sakila.ddm
✅ 解析到 17 个实体

实体列表:
  - actor (演员信息表): 4 个属性, 0 个外键
  - address (地址表): 9 个属性, 1 个外键
  - customer (客户信息表): 9 个属性, 2 个外键
  ...

🔨 生成 OSM 模型...
✅ 生成完成:
  - Ontology 实体: 17
  - Semantic Models: 17
  - Join Graph 边: 21
  - KPIs: 15

💾 保存到: sakila_generated.yaml
✨ 转换完成！
```

## 生成的 OSM 结构

### 1. Ontology Layer（语义真相层）

```yaml
ontology:
  entities:
    Address:
      label: 地址表
      description: 地址表
      attributes:
        address_id:
          label: 地址ID
          type: integer
          physical_type: SMALLINT UNSIGNED
          nullable: false
          semantic_type: identifier
          auto_increment: true
        city_id:
          label: 城市ID
          type: integer
          physical_type: SMALLINT UNSIGNED
          nullable: false
          semantic_type: foreign_key
      relations:
        - name: city-address
          target: City
          cardinality: many_to_one
          inverse: addresss
```

### 2. Semantic Model Layer（数据映射层）

```yaml
semantic_models:
  address:
    entity: Address
    data_source:
      type: mysql
      connection: sakila
    table: address
    primary_key: address_id
    dimensions:
      address_id:
        label: 地址ID
        column: address_id
        type: integer
      city_id:
        label: 城市ID
        column: city_id
        type: integer
    measures: {}
    joins:
      city_join:
        target_model: city
        relationship: many_to_one
        join_type: left
        condition:
          type: key
          local_key: city_id
          foreign_key: city_id
        required: false
```

### 3. Join Graph（连接图）

```yaml
join_graph:
  nodes:
    - actor
    - address
    - city
    - ...
  edges:
    - from: address
      to: city
      join_id: city_join
    - from: customer
      to: address
      join_id: address_join
    - ...
```

### 4. KPI Layer（基础 KPI）

```yaml
kpis:
  address_count:
    name: 地址表数量
    description: 统计地址表的数量
    host:
      entity: Address
      cardinality: many
      grain: entity
    computation:
      type: aggregation
      base_model: address
      measure: count
      aggregation: count
    time:
      dimension: last_update
      grain: [day, week, month, year]
      default_grain: month
```

## 下一步

1. **检查生成的文件**：确认实体、属性、关系是否正确
2. **调整关系类型**：根据业务需求调整 many_to_one、one_to_many 等
3. **添加业务 KPI**：在生成的基础上添加更多有意义的业务指标
4. **完善 Governance**：添加更多的业务规则和权限策略
5. **测试编译**：使用 OSM 编译器测试 IR 到 SQL 的转换

## 常见问题

**Q: 为什么某些实体没有外键？**  
A: 如果实体是主表（如 country、language），它们不会有外键指向其他表。

**Q: 如何修改生成的关系类型？**  
A: 编辑生成的 YAML 文件，修改 `cardinality` 字段（many_to_one、one_to_many、many_to_many）。

**Q: 生成的 KPI 太简单怎么办？**  
A: 这只是基础 KPI（count），你需要根据业务需求手动添加更复杂的 KPI，如收入、增长率等。

**Q: 语义类型推断不准确？**  
A: 编辑生成的 YAML 文件，修改 `semantic_type` 字段。

## 参考

- [OSM 概念说明](docs/OSM_CONCEPTS.md) - 本地文档，详细介绍 OSM 四层架构
- [DDM 格式说明](docs/DDM_FORMAT.md) - DDM XML 格式详解
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题和解决方案
