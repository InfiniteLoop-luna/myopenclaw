"""
ddm_parser.py - 解析 Datablau DDM (XML) 文件

从 DDM 文件中提取：
- 实体（EntityComposite）
- 属性（EntityAttribute）
- 主键 / 唯一键 / 普通索引（EntityKeyGroup）
- 关系（RelationshipRelational，支持复合键）
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Attribute:
    """实体属性"""

    name: str
    label: str  # 中文标签
    data_type: str  # 物理类型，如 VARCHAR(45), SMALLINT UNSIGNED
    nullable: bool
    auto_increment: bool = False
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    order: int = 0


@dataclass
class ForeignKey:
    """外键关系（支持复合键）"""

    name: str
    local_columns: List[str]
    foreign_entity: str
    foreign_columns: List[str]
    relationship: str = "many_to_one"  # many_to_one, one_to_many, one_to_one, many_to_many
    on_delete: Optional[str] = None
    on_update: Optional[str] = None

    # 兼容旧代码（单列 FK）
    @property
    def local_column(self) -> str:
        return self.local_columns[0] if self.local_columns else ""

    @property
    def foreign_column(self) -> str:
        return self.foreign_columns[0] if self.foreign_columns else ""


@dataclass
class Entity:
    """实体定义"""

    name: str
    label: str  # 中文标签
    table_name: str
    attributes: Dict[str, Attribute] = field(default_factory=dict)
    primary_keys: List[str] = field(default_factory=list)
    unique_keys: Dict[str, List[str]] = field(default_factory=dict)
    indexes: Dict[str, List[str]] = field(default_factory=dict)
    foreign_keys: Dict[str, ForeignKey] = field(default_factory=dict)


class DDMParser:
    """DDM XML 解析器"""

    def __init__(self, ddm_path: str):
        self.ddm_path = ddm_path
        self.tree = ET.parse(ddm_path)
        self.root = self.tree.getroot()

        self.entities: Dict[str, Entity] = {}

        # 映射索引
        self.entity_id_to_name: Dict[str, str] = {}
        self.entity_name_to_attr_id_name: Dict[str, Dict[str, str]] = {}
        self.keygroup_id_to_obj: Dict[str, ET.Element] = {}

        # GUID 映射（保留给上层可扩展）
        self.guid_to_entity: Dict[str, str] = {}
        self.guid_to_attribute: Dict[str, tuple] = {}

    def parse(self) -> Dict[str, Entity]:
        """解析 DDM 文件，返回实体字典"""
        self._index_keygroups()
        self._parse_entities()
        self._parse_relations()
        return self.entities

    # ----------------------------
    # 基础工具
    # ----------------------------

    def _get_property_value(self, obj: ET.Element, prop_id: str) -> Optional[str]:
        """获取 Property 节点的 Value"""
        for prop in obj.findall("Property"):
            if prop.get("Id") == prop_id:
                return prop.get("Value")
        return None

    def _to_attr_names(self, entity_name: str, attr_ids: List[str]) -> List[str]:
        """将属性 ID 列表映射为属性名列表"""
        id_name = self.entity_name_to_attr_id_name.get(entity_name, {})
        return [id_name[i] for i in attr_ids if i in id_name]

    def _get_keygroup_member_attr_ids(self, keygroup_obj: ET.Element) -> List[str]:
        """读取 KeyGroup 里的成员属性 ID（支持多列）"""
        attr_ids: List[str] = []
        for member in keygroup_obj.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroupMember']"):
            attr_id = self._get_property_value(member, "80500005")
            if attr_id:
                attr_ids.append(attr_id)
        return attr_ids

    def _resolve_keygroup_columns(self, entity_name: str, keygroup_id: Optional[str]) -> List[str]:
        """通过 KeyGroup ID 解析实际列名（支持复合键）"""
        if not keygroup_id:
            return []
        keygroup_obj = self.keygroup_id_to_obj.get(keygroup_id)
        if keygroup_obj is None:
            return []
        attr_ids = self._get_keygroup_member_attr_ids(keygroup_obj)
        return self._to_attr_names(entity_name, attr_ids)

    @staticmethod
    def _map_cardinality(parent_cardinality: Optional[str], child_cardinality: Optional[str]) -> str:
        """
        将 DDM 基数映射为关系类型（child -> parent 方向）
        """
        one_set = {"ZeroOrOne", "ExactlyOne", "One"}
        many_set = {"ZeroOneOrMore", "OneOrMore", "Many"}

        p = parent_cardinality or ""
        c = child_cardinality or ""

        if p in one_set and c in many_set:
            return "many_to_one"
        if p in many_set and c in one_set:
            return "one_to_many"
        if p in one_set and c in one_set:
            return "one_to_one"
        if p in many_set and c in many_set:
            return "many_to_many"
        return "many_to_one"

    # ----------------------------
    # 第一遍：实体、属性、键组
    # ----------------------------

    def _index_keygroups(self):
        """建立全局 KeyGroup ID -> Object 索引"""
        for keygroup_obj in self.root.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroup']"):
            kg_id = self._get_property_value(keygroup_obj, "90000002")
            if kg_id:
                self.keygroup_id_to_obj[kg_id] = keygroup_obj

    def _parse_entities(self):
        """解析实体、属性、主键/唯一键/索引"""
        entity_nodes = self.root.findall(".//Object[@Type='Datablau.LDM.EntityComposite']")

        for entity_obj in entity_nodes:
            entity_name = self._get_property_value(entity_obj, "90000003")  # 实体名
            if not entity_name:
                continue

            entity_label = self._get_property_value(entity_obj, "80100005") or entity_name
            entity_id = self._get_property_value(entity_obj, "90000002")
            entity_guid = self._get_property_value(entity_obj, "90000006")

            entity = Entity(name=entity_name, label=entity_label, table_name=entity_name)
            self.entities[entity_name] = entity

            if entity_id:
                self.entity_id_to_name[entity_id] = entity_name
            if entity_guid:
                self.guid_to_entity[entity_guid] = entity_name

            # 属性 ID 白名单（部分 DDM 模型中实体下可能嵌有其它对象）
            attr_ids_prop = self._get_property_value(entity_obj, "80100007")
            attr_id_whitelist = set()
            if attr_ids_prop:
                attr_id_whitelist = {x.strip() for x in attr_ids_prop.split(",") if x.strip()}

            attr_id_name: Dict[str, str] = {}
            for attr_obj in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityAttribute']"):
                attr_id = self._get_property_value(attr_obj, "90000002")
                if attr_id_whitelist and attr_id not in attr_id_whitelist:
                    continue

                attr_name = self._get_property_value(attr_obj, "90000003")
                if not attr_name:
                    continue

                attr_label = self._get_property_value(attr_obj, "80100005") or attr_name
                attr_type = self._get_property_value(attr_obj, "80000002") or "STRING"

                # 80100033=True 表示 NOT NULL（见 docs/DDM_FORMAT.md）
                not_null = self._get_property_value(attr_obj, "80100033") == "True"
                attr_nullable = not not_null

                attr_auto_inc = self._get_property_value(attr_obj, "80100035") == "True"
                attr_default = self._get_property_value(attr_obj, "80100034")
                attr_order = int(self._get_property_value(attr_obj, "80400006") or 0)
                attr_guid = self._get_property_value(attr_obj, "90000006")

                attribute = Attribute(
                    name=attr_name,
                    label=attr_label,
                    data_type=attr_type,
                    nullable=attr_nullable,
                    auto_increment=attr_auto_inc,
                    default_value=attr_default,
                    order=attr_order,
                )
                entity.attributes[attr_name] = attribute

                if attr_id:
                    attr_id_name[attr_id] = attr_name
                if attr_guid:
                    self.guid_to_attribute[attr_guid] = (entity_name, attr_name)

            self.entity_name_to_attr_id_name[entity_name] = attr_id_name

            # 键组：主键 / 唯一键 / 普通索引
            for key_group in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroup']"):
                key_type = self._get_property_value(key_group, "80000097")
                key_name = self._get_property_value(key_group, "90000003") or "unnamed_key"

                member_attr_ids = self._get_keygroup_member_attr_ids(key_group)
                key_members = self._to_attr_names(entity_name, member_attr_ids)

                if key_type == "PrimaryKey":
                    entity.primary_keys = key_members
                    for attr_name in key_members:
                        if attr_name in entity.attributes:
                            entity.attributes[attr_name].is_primary_key = True
                elif key_type == "UniqueKey":
                    entity.unique_keys[key_name] = key_members
                elif key_type == "NonUniqueKey":
                    entity.indexes[key_name] = key_members

    # ----------------------------
    # 第二遍：关系
    # ----------------------------

    def _parse_relations(self):
        """解析实体关系（RelationshipRelational）"""
        rel_nodes = self.root.findall(".//Object[@Type='Datablau.LDM.RelationshipRelational']")

        for rel_obj in rel_nodes:
            rel_name = self._get_property_value(rel_obj, "90000003") or "unnamed_relation"

            parent_entity_id = self._get_property_value(rel_obj, "80000052")
            child_entity_id = self._get_property_value(rel_obj, "80000053")
            parent_keygroup_id = self._get_property_value(rel_obj, "80000054")
            child_keygroup_id = self._get_property_value(rel_obj, "80000055")

            parent_cardinality = self._get_property_value(rel_obj, "80000071")
            child_cardinality = self._get_property_value(rel_obj, "80000072")

            on_delete = self._get_property_value(rel_obj, "80500259")
            on_update = self._get_property_value(rel_obj, "80500260")

            parent_entity = self.entity_id_to_name.get(parent_entity_id or "")
            child_entity = self.entity_id_to_name.get(child_entity_id or "")
            if not parent_entity or not child_entity:
                continue

            parent_cols = self._resolve_keygroup_columns(parent_entity, parent_keygroup_id)
            child_cols = self._resolve_keygroup_columns(child_entity, child_keygroup_id)
            if not parent_cols or not child_cols:
                continue

            # 长度对齐：保留配对列（防止异常模型长度不一致）
            pair_len = min(len(parent_cols), len(child_cols))
            parent_cols = parent_cols[:pair_len]
            child_cols = child_cols[:pair_len]
            if pair_len == 0:
                continue

            relationship = self._map_cardinality(parent_cardinality, child_cardinality)

            fk = ForeignKey(
                name=rel_name,
                local_columns=child_cols,
                foreign_entity=parent_entity,
                foreign_columns=parent_cols,
                relationship=relationship,
                on_delete=on_delete,
                on_update=on_update,
            )

            if child_entity in self.entities:
                self.entities[child_entity].foreign_keys[rel_name] = fk

                # 标记外键列
                for col in child_cols:
                    if col in self.entities[child_entity].attributes:
                        self.entities[child_entity].attributes[col].is_foreign_key = True


def main():
    """测试解析器"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ddm_parser.py <ddm_file>")
        sys.exit(1)

    parser = DDMParser(sys.argv[1])
    entities = parser.parse()

    print(f"解析到 {len(entities)} 个实体：")
    for entity_name, entity in entities.items():
        print(f"\n实体: {entity_name} ({entity.label})")
        print(f"  属性数: {len(entity.attributes)}")
        print(f"  主键: {entity.primary_keys}")
        print(f"  唯一键数: {len(entity.unique_keys)}")
        print(f"  外键数: {len(entity.foreign_keys)}")
        print(f"  索引数: {len(entity.indexes)}")


if __name__ == "__main__":
    main()
