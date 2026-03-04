# OSM (Ontology-Lite Semantic Model) 概念说明

## 什么是 OSM？

OSM (Ontology-Lite Semantic Model) 是一个**四层语义模型标准**，用于构建可编译（AI）、可治理（企业级）、可推理（语义一致）、可执行（生成 SQL）的企业语义系统。

## 为什么需要 OSM？

传统的数据查询方式：
- ❌ 用户需要懂 SQL
- ❌ 需要了解数据库表结构
- ❌ 业务逻辑分散在各处
- ❌ 权限控制困难

使用 OSM 后：
- ✅ 用户用自然语言提问
- ✅ AI 生成结构化 IR（中间表示）
- ✅ 语义层自动编译成 SQL
- ✅ 统一的业务逻辑和权限控制

## OSM 四层架构

```
┌─────────────────────────────────────────┐
│  用户自然语言问题                          │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  AI 生成 IR (Intermediate Representation) │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  OSM 四层语义模型                          │
│  ┌─────────────────────────────────┐    │
│  │ 1. Ontology Layer (语义真相层)   │    │
│  │    - 实体、属性、关系定义          │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 2. Semantic Model Layer (映射层) │    │
│  │    - 数据源映射、Join、Filter     │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 3. KPI Layer (业务指标层)        │    │
│  │    - KPI 定义、计算逻辑           │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ 4. Governance Layer (治理层)     │    │
│  │    - 规则、权限、安全策略          │    │
│  └─────────────────────────────────┘    │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│  生成 SQL 并执行                          │
└─────────────────────────────────────────┘
```

## 第一层：Ontology Layer（语义真相层）

**目标**：定义企业的"语义世界"，不涉及具体数据库实现。

### 核心概念

#### 1. Entity（实体）
企业中的核心对象，如客户、产品、订单等。

```yaml
ontology:
  entities:
    Customer:
      label: 客户
      description: 客户基本信息
      attributes: {...}
      relations: [...]
```

#### 2. Attribute（属性）
实体的特征，包含类型、可空性、语义类型等。

```yaml
attributes:
  customer_id:
    label: 客户ID
    type: integer
    physical_type: INT
    nullable: false
    semantic_type: identifier
  email:
    label: 电子邮件
    type: string
    physical_type: VARCHAR(100)
    nullable: true
    semantic_type: email
```

**语义类型**：
- `identifier` - 唯一标识符
- `name` - 名称
- `email` - 电子邮件
- `phone` - 电话号码
- `currency` - 货币金额
- `percentage` - 百分比
- `timestamp` - 时间戳
- `status` - 状态

#### 3. Relation（关系）
实体之间的逻辑关联。

```yaml
relations:
  - name: belongs_to_store
    target: Store
    cardinality: many_to_one
    inverse: customers
```

**基数类型**：
- `one_to_one` - 一对一
- `one_to_many` - 一对多
- `many_to_one` - 多对一
- `many_to_many` - 多对多

## 第二层：Semantic Model Layer（数据映射层）

**目标**：将 Ontology 实体映射到物理数据源。

### 核心概念

#### 1. Data Source（数据源）
```yaml
semantic_models:
  customers:
    entity: Customer
    data_source:
      type: mysql
      connection: main_db
    table: customer
    primary_key: customer_id
```

#### 2. Dimensions（维度）
用于分组、筛选的字段。

```yaml
dimensions:
  customer_name:
    label: 客户名称
    column: name
    type: string
  region:
    label: 地区
    column: region
    type: string
```

#### 3. Measures（度量）
用于聚合计算的数值字段。

```yaml
measures:
  total_amount:
    label: 总金额
    column: amount
    aggregation: sum
    type: decimal
```

#### 4. Joins（连接）
定义表之间的连接关系。

```yaml
joins:
  store_join:
    target_model: stores
    relationship: many_to_one
    join_type: left
    condition:
      type: key
      local_key: store_id
      foreign_key: store_id
    required: false
```

## 第三层：KPI Layer（业务指标层）

**目标**：定义企业级业务指标。

### KPI 结构

```yaml
kpis:
  store_revenue:
    name: 门店收入
    description: 各门店在指定时间范围内的收入总额
    
    host:
      entity: Store
      cardinality: many
      grain: entity
    
    computation:
      type: aggregation
      base_model: payments
      measure: total_amount
      aggregation: sum
      filters: []
      joins: []
    
    time:
      dimension: payment_date
      grain: [day, week, month, year]
      default_grain: month
    
    output:
      type: vector
      format: currency
```

### KPI 类型

1. **Aggregation KPI**（聚合型）
   - 直接聚合计算：sum、count、avg、min、max

2. **Derived KPI**（派生型）
   - 基于其他 KPI 计算：增长率、同比、环比

3. **Formula KPI**（公式型）
   - 多个度量的计算：客均收入 = 总收入 / 客户数

4. **Ratio KPI**（比率型）
   - 百分比计算：转化率、占比

## 第四层：Governance Layer（治理层）

**目标**：保证数据安全、权限控制、规则约束。

### 1. Rules（规则）

```yaml
governance:
  rules:
    - id: require_time_dimension
      condition: kpi.time.dimension is not None
      action: enforce_time_dimension
      description: 所有 KPI 必须指定时间维度
```

### 2. Policies（策略）

#### 行级安全（Row-Level Security）
```yaml
policies:
  row_level:
    - entity: Store
      filter: store_id = ${user.store_id}
```

#### 角色权限
```yaml
role_permissions:
  finance_manager:
    allowed_kpis:
      - store_revenue
      - revenue_growth
    allowed_entities:
      - Store
      - Payment
  
  store_manager:
    allowed_kpis:
      - store_revenue
    allowed_entities:
      - Store
```

## IR（中间表示）

IR 是用户问题和 OSM 之间的桥梁。

### IR 示例

用户问题：
> "北区最近一年的门店收入增长率如何？"

AI 生成 IR：
```json
{
  "version": "1.0",
  "kpi": "revenue_growth",
  "host": {
    "entity": "Store"
  },
  "time": {
    "grain": "month",
    "range": {
      "type": "relative",
      "value": "last_12_months"
    }
  },
  "filters": [
    {
      "field": "region",
      "operator": "=",
      "value": "北区"
    }
  ]
}
```

### IR 执行流程

```
IR → Validator → Optimizer → Planner → SQL → Database
```

1. **Validator**：校验 IR 是否合法
2. **Optimizer**：优化 IR（展开依赖、下推过滤）
3. **Planner**：生成执行计划
4. **SQL Generator**：生成 SQL
5. **Executor**：执行查询

## OSM 的优势

### 1. 语义一致性
- 统一的业务术语
- 单一真相源（Single Source of Truth）
- 避免数据口径不一致

### 2. AI 友好
- 结构化的语义模型
- 可编译的 IR
- 自动生成 SQL

### 3. 企业级治理
- 权限控制
- 行级安全
- 审计追踪

### 4. 可维护性
- 业务逻辑集中管理
- 修改一处，全局生效
- 版本控制

### 5. 可扩展性
- 支持多数据源
- 支持复杂 KPI
- 支持自定义规则

## 实际应用场景

### 场景 1：自然语言查询

**用户**："上个月销售额最高的 10 个产品是什么？"

**系统流程**：
1. AI 理解意图 → 生成 IR
2. IR 经过语义层校验
3. 语义层生成 SQL
4. 执行并返回结果
5. AI 用自然语言解释结果

### 场景 2：权限控制

**区域经理**只能看到自己区域的数据：
- 系统自动在 IR 中注入 `region = "华东区"` 过滤条件
- 用户无感知，但数据已被限制

### 场景 3：指标一致性

**财务部门**和**销售部门**使用同一个 `revenue` KPI：
- 计算逻辑统一定义在 OSM 中
- 避免"各说各话"的情况

## 总结

OSM 是一个**语义层标准**，它：
- 📚 定义了企业的语义世界（Ontology）
- 🔗 连接了语义和物理数据（Semantic Model）
- 📊 管理了业务指标（KPI）
- 🔒 保证了安全和治理（Governance）
- 🤖 让 AI 能够理解和查询数据（IR）

通过 OSM，企业可以构建一个**可编译的语义数据平台**，让数据查询变得简单、安全、一致。
