# DDM (Data Definition Model) 格式说明

## 什么是 DDM？

DDM (Data Definition Model) 是 **Datablau** 数据建模工具生成的数据库模型文件，采用 XML 格式存储。

## DDM 文件结构

### 1. 文件头

```xml
<File>
  <Header 
    RepositoryId="" 
    ModelId="0" 
    MetaVersion="1.0.1" 
    Version="" 
    FilePath="D:\model\sakila.ddm" 
  />
  <Model Seed="370" SeedMax="0" Type="Datablau.LDM.ModelSource">
    ...
  </Model>
</File>
```

### 2. 核心对象类型

#### EntityComposite（实体/表）

表示数据库中的表。

```xml
<Object Type="Datablau.LDM.EntityComposite">
  <Property Id="90000001" Type="System.Int32" Value="80000004" />
  <Property Id="90000002" Type="System.Int32" Value="3" />
  <Property Id="90000003" Type="System.String" Value="actor" />
  <Property Id="90000006" Type="System.Guid" Value="..." />
  <Property Id="80100005" Type="System.String" Value="演员信息表" />
  ...
</Object>
```

**关键属性 ID**：
- `90000002` - 实体序号（用于关系引用）
- `90000003` - 实体名称（表名）
- `90000006` - 实体 GUID
- `80100005` - 中文标签
- `80100007` - 属性 ID 列表（逗号分隔）

#### EntityAttribute（属性/列）

表示表中的列。

```xml
<Object Type="Datablau.LDM.EntityAttribute">
  <Property Id="90000002" Type="System.Int32" Value="22" />
  <Property Id="90000003" Type="System.String" Value="actor_id" />
  <Property Id="90000006" Type="System.Guid" Value="..." />
  <Property Id="80000002" Type="System.String" Value="SMALLINT UNSIGNED" />
  <Property Id="80100005" Type="System.String" Value="演员ID" />
  <Property Id="80100033" Type="System.Boolean" Value="True" />
  <Property Id="80100035" Type="System.Boolean" Value="True" />
  <Property Id="80100034" Type="System.String" Value="CURRENT_TIMESTAMP" />
  <Property Id="80400006" Type="System.Int32" Value="1" />
</Object>
```

**关键属性 ID**：
- `90000002` - 属性序号
- `90000003` - 属性名称（列名）
- `90000006` - 属性 GUID
- `80000002` - 数据类型（如 VARCHAR(45), INT）
- `80100005` - 中文标签
- `80100033` - 是否非空（True = NOT NULL）
- `80100035` - 是否自增（True = AUTO_INCREMENT）
- `80100034` - 默认值
- `80400006` - 列顺序

#### EntityKeyGroup（键组）

表示主键、外键、索引等。

```xml
<Object Type="Datablau.LDM.EntityKeyGroup">
  <Property Id="90000002" Type="System.Int32" Value="34" />
  <Property Id="90000003" Type="System.String" Value="PK_actor" />
  <Property Id="90000006" Type="System.Guid" Value="..." />
  <Property Id="80000096" Type="System.String" Value="35" />
  <Property Id="80000097" Type="Datablau.LDM.KeyGroupType" Value="PrimaryKey" />
  <Property Id="80500152" Type="System.String" Value="BTREE" />
  ...
</Object>
```

**关键属性 ID**：
- `90000002` - 键组序号
- `90000003` - 键组名称
- `80000096` - 成员 ID 列表
- `80000097` - 键组类型：
  - `PrimaryKey` - 主键
  - `ForeignKey` - 外键
  - `NonUniqueKey` - 普通索引
  - `UniqueKey` - 唯一索引
- `80500152` - 索引类型（BTREE, HASH）

#### EntityKeyGroupMember（键组成员）

键组中包含的列。

```xml
<Object Type="Datablau.LDM.EntityKeyGroupMember">
  <Property Id="90000002" Type="System.Int32" Value="35" />
  <Property Id="90000003" Type="System.String" Value="KeyGroupMember_35" />
  <Property Id="90000006" Type="System.Guid" Value="..." />
  <Property Id="80500005" Type="System.Int32" Value="22" />
</Object>
```

**关键属性 ID**：
- `90000002` - 成员序号
- `80500005` - 引用的属性序号（指向 EntityAttribute 的 90000002）

#### RelationshipRelational（关系）

表示表之间的外键关系。

```xml
<Object Type="Datablau.LDM.RelationshipRelational">
  <Property Id="90000002" Type="System.Int32" Value="295" />
  <Property Id="90000003" Type="System.String" Value="city-address" />
  <Property Id="90000006" Type="System.Guid" Value="..." />
  <Property Id="80000021" Type="System.String" Value="ref to" />
  <Property Id="80000052" Type="System.Int32" Value="6" />
  <Property Id="80000053" Type="System.Int32" Value="4" />
  <Property Id="80000054" Type="System.Int32" Value="54" />
  <Property Id="80000055" Type="System.Int32" Value="37" />
  <Property Id="80000070" Type="Datablau.LDM.RelationalType" Value="NonIdentifying" />
  <Property Id="80000071" Type="Datablau.LDM.CardinalityType" Value="ZeroOrOne" />
  <Property Id="80000072" Type="Datablau.LDM.CardinalityType" Value="ZeroOneOrMore" />
  <Property Id="80500259" Type="System.String" Value="CASCADE" />
  <Property Id="80500260" Type="System.String" Value="RESTRICT" />
</Object>
```

**关键属性 ID**：
- `90000002` - 关系序号
- `90000003` - 关系名称
- `80000052` - 父实体序号（指向 EntityComposite 的 90000002）
- `80000053` - 子实体序号
- `80000054` - 父键组序号（指向 EntityKeyGroup 的 90000002）
- `80000055` - 子键组序号
- `80000070` - 关系类型：
  - `Identifying` - 标识关系
  - `NonIdentifying` - 非标识关系
- `80000071` - 父基数：
  - `ZeroOrOne` - 0..1
  - `ExactlyOne` - 1
  - `ZeroOneOrMore` - 0..*
- `80000072` - 子基数
- `80500259` - ON DELETE 动作（CASCADE, RESTRICT, SET NULL）
- `80500260` - ON UPDATE 动作

## 解析流程

### 1. 解析实体

```
遍历所有 EntityComposite
  ├─ 读取实体名称 (90000003)
  ├─ 读取中文标签 (80100005)
  ├─ 读取属性 ID 列表 (80100007)
  └─ 遍历 EntityAttribute
      ├─ 读取属性名称 (90000003)
      ├─ 读取数据类型 (80000002)
      ├─ 读取中文标签 (80100005)
      └─ 读取约束（非空、自增、默认值）
```

### 2. 解析主键和索引

```
遍历所有 EntityKeyGroup
  ├─ 读取键组类型 (80000097)
  └─ 遍历 EntityKeyGroupMember
      └─ 读取引用的属性 ID (80500005)
```

### 3. 解析关系

```
遍历所有 RelationshipRelational
  ├─ 读取父实体 ID (80000052)
  ├─ 读取子实体 ID (80000053)
  ├─ 读取父键组 ID (80000054)
  ├─ 读取子键组 ID (80000055)
  ├─ 通过键组 ID 查找 EntityKeyGroup
  ├─ 通过键组成员查找实际的列
  └─ 建立外键关系
```

## 常见问题

### Q: 为什么关系中的键 ID 不是直接的属性 ID？

A: DDM 使用 KeyGroup 作为中间层，关系引用的是 KeyGroup ID，需要通过 KeyGroup 的成员来找到实际的属性。

### Q: 如何区分主键和外键？

A: 通过 EntityKeyGroup 的 `80000097` 属性：
- `PrimaryKey` = 主键
- `ForeignKey` = 外键

### Q: 基数如何映射到关系类型？

A: 
- 父 `ZeroOrOne` + 子 `ZeroOneOrMore` = `many_to_one`
- 父 `ZeroOneOrMore` + 子 `ZeroOrOne` = `one_to_many`
- 父 `ZeroOrOne` + 子 `ZeroOrOne` = `one_to_one`
- 父 `ZeroOneOrMore` + 子 `ZeroOneOrMore` = `many_to_many`

### Q: 如何处理多列主键/外键？

A: EntityKeyGroup 可以包含多个 EntityKeyGroupMember，每个成员引用一个列。

## 示例：完整的解析流程

假设有一个 `city-address` 关系：

1. **RelationshipRelational** 说：
   - 父实体 ID = 6 (city)
   - 子实体 ID = 4 (address)
   - 父键组 ID = 54
   - 子键组 ID = 37

2. **查找父键组** (ID=54)：
   - 类型 = PrimaryKey
   - 名称 = PK_city
   - 成员引用属性 ID = 48

3. **查找子键组** (ID=37)：
   - 类型 = ForeignKey
   - 名称 = fk_address_city
   - 成员引用属性 ID = 27

4. **查找属性**：
   - 属性 ID=48 → city.city_id
   - 属性 ID=27 → address.city_id

5. **建立关系**：
   - address.city_id → city.city_id
   - 关系类型 = many_to_one

## 工具支持

本 skill 支持解析以下 DDM 对象：
- ✅ EntityComposite
- ✅ EntityAttribute
- ✅ EntityKeyGroup (PrimaryKey, ForeignKey, NonUniqueKey)
- ✅ EntityKeyGroupMember
- ✅ RelationshipRelational
- ❌ EntityView（视图，暂不支持）
- ❌ StoredProcedure（存储过程，暂不支持）

## 参考

- Datablau 官方文档
- DDM XML Schema
- 本 skill 的解析器实现：`scripts/ddm_parser.py`
