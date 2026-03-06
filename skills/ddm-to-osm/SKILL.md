# DDM to OSM Converter Skill

自动将 Datablau DDM (Data Definition Model) 转换为 OSM (Ontology-Lite Semantic Model) YAML。

## P2 版本能力

### 核心能力
1. **Ontology Layer**：实体、属性、关系、约束、枚举
2. **Semantic Model Layer**：数据源映射、维度、度量、Join、静态 Filter
3. **KPI Layer**：基础聚合 + 派生指标 + 结构标准化
4. **Governance Layer**：基础规则与角色权限（支持 curated 联动）
5. **Release & Diff Layer（P2）**：版本追踪、差异报告、发布产物流水

### P2 增强点
- 复合外键解析（multi-column FK）
- 主键 / 唯一键 / 索引解析增强
- 语义类型推断边界匹配（减少误判）
- inverse 命名修复（避免 `addresss/citys`）
- Ontology 增加 `constraints` / `enums`（自动 + profile）
- Semantic Model 增加 `filters`（自动 + profile）
- join 支持 profile 覆写到 `expression` / `temporal_validity`
- KPI `time` 结构统一
- KPI 自动补齐 `constraints` / `dependencies`
- 支持 `--kpi-mode basic|advanced`
- 支持 `--profile <yaml>`
- `convert.py` 支持 `--report`
- meta 增加 `model_version` / `source_fingerprint`
- 新增 `lint_osm.py` 一致性检查
- `curate_kpi_pack.py` 支持依赖补全与权限联动
- 新增 `diff_osm.py` 结构化差异报告
- 新增 `make_release_artifacts.py` 一键生成发布产物 + manifest

---

## 使用方法

### 基础用法

```bash
python convert.py <ddm_file> <output_yaml> [database_name]
```

### 推荐用法

```bash
# advanced KPI（默认）
python convert.py sakila.ddm sakila_osm.yaml sakila

# basic KPI
python convert.py sakila.ddm sakila_osm_basic.yaml sakila --kpi-mode basic

# 使用 profile 覆写规则
python convert.py sakila.ddm sakila_osm_profiled.yaml sakila --profile profile.example.yaml

# 生成转换报告（P2）
python convert.py sakila.ddm sakila_osm_profiled.yaml sakila --profile profile.example.yaml --report sakila.report.md

# lint 检查
python lint_osm.py sakila_osm_profiled.yaml

# curated KPI 包（自动补依赖）
python curate_kpi_pack.py sakila_osm_profiled.yaml sakila_top30.yaml --top 30

# 生成差异报告（P2）
python diff_osm.py old.yaml new.yaml --md diff.md --json diff.json

# 一键发布产物流水（P2）
python make_release_artifacts.py sakila.ddm release_out sakila --profile profile.example.yaml --kpi-mode advanced --top 30 --baseline old.yaml
```

### 参数说明（convert.py）

- `ddm_file`：DDM 文件路径（.ddm）
- `output_yaml`：输出 OSM YAML 文件路径
- `database_name`：数据库名称（可选，默认 `database`）
- `--kpi-mode`：`basic` 或 `advanced`（默认 `advanced`）
- `--profile`：YAML 配置文件路径（可选）
- `--report`：Markdown 报告路径（可选，P2）

---

## profile 配置示例

```yaml
data_source:
  type: mysql
  connection: sakila

ontology_rules:
  entities:
    Customer:
      constraints:
        - type: required_relation
          rule: Customer must belong to Store
      enums:
        vip_level: [normal, silver, gold, platinum]

semantic_rules:
  joins:
    payment:
      rental_payment_join:
        condition:
          type: expression
          expression: payment.rental_id = rental.rental_id
  filters:
    customer:
      region_scope:
        expression:
          type: condition
          field: store_id
          operator: in
          value: [1, 2, 3]
```

---

## 输出结构（关键字段）

### meta（P2）

```yaml
meta:
  schema_version: osm-v1.0
  generator: ddm-to-osm
  generator_version: 1.2.0-p1
  generated_at: 2026-03-06T...
  kpi_mode: basic|advanced
  model_version: v1
  source_fingerprint: sha256:...
```

### Ontology 新字段

```yaml
ontology:
  entities:
    Customer:
      constraints: []
      enums: {}
```

### Semantic Model 新字段

```yaml
semantic_models:
  customer:
    joins: {}
    filters: {}
```

### KPI 标准字段

```yaml
kpis:
  payment_amount_sum:
    time:
      dimension: payment_date
      default_grain: month
      allowed_grains: [day, week, month, quarter, year]
      window: null
    constraints:
      require_time: true
      require_host: true
      allowed_filters: []
    dependencies:
      metrics: []
      entities: [Payment]
```

---

## 发布产物（P2）

`make_release_artifacts.py` 默认输出：
- `<name>.osm.yaml`
- `<name>.report.md`
- `<name>.topN.yaml`
- `<name>.topN.report.md`
- `<name>.diff.md` / `<name>.diff.json`（有 baseline 时）
- `manifest.json`

---

## 测试

```bash
python test.py
```

覆盖：
- parser/generator/golden 回归
- P1 字段回归（constraints/enums/filters/KPI 标准字段）
- profile 覆写回归（expression join / filters / enums）
- lint + curate + governance 一致性回归
- P2 回归（meta 指纹/version、report、diff、release manifest）

---

## 相关资源

- [README.md](README.md)
- [EXAMPLE.md](EXAMPLE.md)
- [OSM 概念说明](docs/OSM_CONCEPTS.md)
- [DDM 格式说明](docs/DDM_FORMAT.md)
- [故障排除](docs/TROUBLESHOOTING.md)
