# Task: osi-adoption（规划任务，暂不执行）

> 状态：**Planned**
> 执行策略：**冻结实现，仅保留方案与验收标准，等待明确指令后再开始开发**。

## 1. 背景

当前已有 `skills/ddm-to-osm`，可将 Datablau DDM 转为内部 OSM（Ontology-Lite Semantic Model）四层结构（Ontology / Semantic Model / KPI / Governance）。

为提升跨工具互操作性，计划引入 OSI（Open Semantic Interchange）作为**对外交换标准**。

## 2. 目标

构建“双层模型策略”：

- **内部执行层**：继续使用 OSM（完整业务语义与治理能力）
- **外部交换层**：输出 OSI（vendor-agnostic，跨工具可交换）

并建立统一中间层，支持多出口：

`DDM -> semantic_graph -> OSM / OSI`

## 3. 非目标（当前不做）

- 不重写现有 `ddm-to-osm` 全量逻辑
- 不一次性接入所有 BI/AI 平台
- 不在本任务阶段内实现全量治理规则标准化（先通过扩展字段保真）

## 4. 方案总览

### 4.1 核心架构

1. 解析层：`ddm_parser`（保留）
2. 中间层：`semantic_graph_builder`（新增）
3. 输出层：
   - `osm_emitter`（重构）
   - `osi_emitter`（新增）
4. 校验层：
   - OSI schema 校验
   - 映射完整性报告（mapping report）

### 4.2 关键映射原则

- OSM Ontology -> OSI datasets/fields + ai_context + custom_extensions
- OSM Semantic Model -> OSI datasets/relationships
- OSM KPI -> OSI metrics（无法直映的 host/grain/time 放 extensions）
- OSM Governance -> OSI custom_extensions（无损优先）

### 4.3 交付产物（目标）

- `model.osm.yaml`
- `model.osi.yaml`
- `mapping-report.json`（字段映射、降级、扩展承载记录）

## 5. 分阶段里程碑

### Phase 0：设计冻结
- 定义 `semantic_graph` 数据结构
- 明确命名规范与映射字典
- 输出设计文档 + 风险清单

### Phase 1：最小可用
- 实现 `--format osi`
- 生成 OSI YAML
- 接入 OSI schema 校验

### Phase 2：双格式一致性
- 支持 `--format both`
- 产出 mapping-report
- 对 Sakila 样例做一致性验证

### Phase 3：可运维化
- 增量变更 diff 报告
- 破坏性变更告警策略
- 模型版本化与发布规程

## 6. 验收标准（Definition of Done）

- [ ] DDM->OSI 成功率 >= 95%（样例库）
- [ ] OSI schema 校验通过率 100%（输出文件）
- [ ] OSM/OSI 核心实体与关系数量偏差 <= 5%
- [ ] 所有无法直映字段在 mapping-report 中可追溯
- [ ] CLI 支持：`--format osm|osi|both`

## 7. 风险与缓解

1. **语义损失风险**：OSI核心字段无法覆盖治理语义
   - 缓解：统一落 `custom_extensions` + 映射报告追踪
2. **双标准漂移风险**：OSM与OSI演化不同步
   - 缓解：引入语义中间层作为唯一源
3. **维护复杂度上升**：多出口导致成本增加
   - 缓解：先做最小可用，逐步扩展

## 8. 执行开关（非常重要）

本任务当前仅记录，不执行实现。

仅当出现以下明确口令之一时，才开始开发执行：

- `开始执行任务：osi-adoption`
- `按 tasks/osi-adoption 方案开始实现`

若无上述口令，仅允许更新文档，不进行代码实现。

## 9. 建议首次执行顺序（未来）

1. 先做 `semantic_graph` + `osi_emitter` MVP
2. 对 sakila.ddm 跑通 `--format osi`
3. 再接 `--format both` 与 mapping-report

