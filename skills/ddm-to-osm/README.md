# DDM to OSM Converter

将 Datablau DDM (Data Definition Model) 自动转换为 OSM (Ontology-Lite Semantic Model) YAML。

## 当前版本亮点（P2）

- ✅ 复合外键解析（multi-column FK）
- ✅ 主键 / 唯一键 / 索引解析增强
- ✅ 语义类型推断改进（边界匹配，降低误判）
- ✅ 关系反向命名修复（如 `city -> cities`, `address -> addresses`）
- ✅ KPI 时间结构统一（`dimension/default_grain/allowed_grains/window`）
- ✅ KPI 结构规范化（`constraints` / `dependencies` 补齐）
- ✅ Ontology 增加 `constraints` / `enums`
- ✅ Semantic Model 增加 `filters`，join 支持 `expression` / `temporal_validity` 覆写
- ✅ 支持 `--kpi-mode basic|advanced`
- ✅ 支持 `--profile <yaml>` 配置化生成
- ✅ `convert.py` 支持 `--report`（生成报告）
- ✅ meta 版本与来源指纹（`model_version` / `source_fingerprint`）
- ✅ 新增 `lint_osm.py` 一致性检查
- ✅ `curate_kpi_pack.py` 增强：依赖闭包补全 + governance 权限联动
- ✅ 新增 `diff_osm.py`（OSM 差异报告）
- ✅ 新增 `make_release_artifacts.py`（一键发布产物流水）
- ✅ 增强测试（覆盖 P0/P1/P2 回归）

---

## 文件结构

```text
ddm-to-osm/
├── README.md
├── SKILL.md
├── EXAMPLE.md
├── CHANGELOG.md
├── convert.py
├── test.py
├── lint_osm.py
├── curate_kpi_pack.py
├── diff_osm.py
├── make_release_artifacts.py
├── requirements.txt
├── profile.example.yaml
├── scripts/
│   ├── ddm_parser.py
│   └── osm_generator.py
└── docs/
    ├── OSM_CONCEPTS.md
    ├── DDM_FORMAT.md
    └── TROUBLESHOOTING.md
```

---

## 快速使用

```bash
# 1) 安装依赖
pip install -r requirements.txt

# 2) 基础转换（advanced KPI）
python convert.py sakila.ddm sakila_osm.yaml sakila

# 3) 仅生成基础 KPI
python convert.py sakila.ddm sakila_osm_basic.yaml sakila --kpi-mode basic

# 4) 使用 profile 覆写规则
python convert.py sakila.ddm sakila_osm_profiled.yaml sakila --profile profile.example.yaml

# 5) 生成报告（P2）
python convert.py sakila.ddm sakila_osm_profiled.yaml sakila --profile profile.example.yaml --report sakila.report.md

# 6) lint 检查
python lint_osm.py sakila_osm_profiled.yaml

# 7) 筛选高价值 KPI 包（自动补依赖）
python curate_kpi_pack.py sakila_osm_profiled.yaml sakila_top30.yaml --top 30

# 8) OSM diff 报告（P2）
python diff_osm.py old.yaml new.yaml --md diff.md --json diff.json

# 9) 一键发布产物流水（P2）
python make_release_artifacts.py sakila.ddm release_out sakila --profile profile.example.yaml --kpi-mode advanced --top 30 --baseline old.yaml
```

## 命令模板（复制即用）

```bash
# A. 最小可用：DDM -> OSM
python convert.py <input.ddm> <output.yaml> <database_name>

# B. 配置化转换（推荐）
python convert.py <input.ddm> <output.yaml> <database_name> \
  --profile <profile.yaml> \
  --kpi-mode advanced \
  --report <report.md>

# C. 质量治理检查（lint）
python lint_osm.py <output.yaml> --strict

# D. 生成高价值 KPI 包（自动补齐依赖）
python curate_kpi_pack.py <output.yaml> <top_pack.yaml> --top 30 --report <top_pack.report.md>

# E. 版本差异对比
python diff_osm.py <old.yaml> <new.yaml> --md <diff.md> --json <diff.json>

# F. 一键发布产物（最完整）
python make_release_artifacts.py <input.ddm> <release_dir> <database_name> \
  --profile <profile.yaml> \
  --kpi-mode advanced \
  --top 30 \
  --baseline <old.yaml>
```

---

## 参数说明

- `ddm_file`：输入 DDM 文件路径（.ddm）
- `output_yaml`：输出 OSM YAML 文件路径
- `database_name`：数据库名（可选，默认 `database`）
- `--kpi-mode`：`basic` 或 `advanced`（默认 `advanced`）
- `--profile`：YAML 配置文件（可选）
- `--report`：转换报告输出路径（可选，P2）

---

## 输出能力概览

### Ontology Layer
- 实体 / 属性 / 关系
- 属性语义类型推断（identifier、foreign_key、name、email、currency...）
- `constraints`（自动 + profile 补充）
- `enums`（自动 + profile 补充）

### Semantic Model Layer
- 数据源映射、主键、维度、度量
- Join 定义（支持单列和复合键）
- `filters`（自动模板 + profile 合并）
- join 支持 profile 覆写为 expression/temporal_validity

### Join Graph
- 自动生成节点与边

### KPI Layer
- `basic`：基础聚合 KPI（count/sum/avg/max/min/distinct）
- `advanced`：在 basic 基础上增加公式派生 + YoY/MoM
- 所有 KPI 自动标准化：
  - `time`: `dimension/default_grain/allowed_grains/window`
  - `constraints`: `require_time/require_host/allowed_filters`
  - `dependencies`: `metrics/entities`

### Governance Layer
- 基础规则和角色权限策略
- curated KPI 包时自动同步 `allowed_kpis`

### P2 治理化能力
- `meta.model_version`
- `meta.source_fingerprint`（DDM 内容指纹）
- 报告产出（generation report）
- 差异对比（diff report）
- 发布清单（manifest.json）

---

## 典型测试结果（sakila）

- 解析实体：17
- Join Graph 边：21
- KPI：
  - `basic` = 70
  - `advanced` = 198
- curated top30（含依赖补全）≈ 32
- lint：advanced / curated 均可通过

---

## 测试

```bash
python test.py
```

测试覆盖：
- 环境与依赖
- parser/generator 导入
- sakila golden 回归
- P1 结构回归（constraints/enums/filters/KPI 标准字段）
- profile 覆写回归（expression join / filters / enums）
- lint + curate + governance 一致性回归
- P2 回归（meta 指纹/version、report、diff、release manifest）

---

## 相关文档

- [SKILL.md](SKILL.md)
- [EXAMPLE.md](EXAMPLE.md)
- [OSM 概念](docs/OSM_CONCEPTS.md)
- [DDM 格式](docs/DDM_FORMAT.md)
- [故障排除](docs/TROUBLESHOOTING.md)
