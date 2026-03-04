"""
ddm_parser.py - 解析 Datablau DDM (XML) 文件

从 DDM 文件中提取：
- 实体（EntityComposite）
- 属性（EntityAttribute）
- 主键（EntityKeyGroup with PrimaryKey）
- 索引（EntityKeyGroup with NonUniqueKey）
- 关系（通过外键推断）
"""
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from dataclasses import dataclass, field


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
class Entity:
    """实体定义"""
    name: str
    label: str  # 中文标签
    table_name: str
    attributes: Dict[str, Attribute] = field(default_factory=dict)
    primary_keys: List[str] = field(default_factory=list)
    indexes: Dict[str, List[str]] = field(default_factory=dict)
    foreign_keys: Dict[str, 'ForeignKey'] = field(default_factory=dict)


@dataclass
class ForeignKey:
    """外键关系"""
    name: str
    local_column: str
    foreign_entity: str
    foreign_column: str
    relationship: str = "many_to_one"  # many_to_one, one_to_many, many_to_many


class DDMParser:
    """DDM XML 解析器"""
    
    def __init__(self, ddm_path: str):
        self.ddm_path = ddm_path
        self.tree = ET.parse(ddm_path)
        self.root = self.tree.getroot()
        self.entities: Dict[str, Entity] = {}
        self.guid_to_entity: Dict[str, str] = {}  # GUID -> entity_name
        self.guid_to_attribute: Dict[str, tuple] = {}  # GUID -> (entity_name, attr_name)
        
    def parse(self) -> Dict[str, Entity]:
        """解析 DDM 文件，返回实体字典"""
        # 第一遍：解析所有实体和属性
        self._parse_entities()
        # 第二遍：解析关系（外键）
        self._parse_relations()
        return self.entities
    
    def _get_property_value(self, obj: ET.Element, prop_id: str) -> Optional[str]:
        """获取 Property 节点的值"""
        for prop in obj.findall('Property'):
            if prop.get('Id') == prop_id:
                return prop.get('Value')
        return None
    
    def _parse_entities(self):
        """解析实体和属性"""
        # 查找所有 EntityComposite
        for entity_obj in self.root.findall(".//Object[@Type='Datablau.LDM.EntityComposite']"):
            entity_name = self._get_property_value(entity_obj, '90000003')  # 实体名称
            entity_label = self._get_property_value(entity_obj, '80100005') or entity_name  # 中文标签
            entity_guid = self._get_property_value(entity_obj, '90000006')
            
            if not entity_name:
                continue
            
            entity = Entity(
                name=entity_name,
                label=entity_label,
                table_name=entity_name  # 默认表名与实体名相同
            )
            
            self.entities[entity_name] = entity
            self.guid_to_entity[entity_guid] = entity_name
            
            # 解析属性
            attr_ids = self._get_property_value(entity_obj, '80100007')  # 属性 ID 列表
            if attr_ids:
                attr_id_list = [aid.strip() for aid in attr_ids.split(',')]
                for attr_obj in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityAttribute']"):
                    attr_id = self._get_property_value(attr_obj, '90000002')
                    if attr_id not in attr_id_list:
                        continue
                    
                    attr_name = self._get_property_value(attr_obj, '90000003')
                    attr_label = self._get_property_value(attr_obj, '80100005') or attr_name
                    attr_type = self._get_property_value(attr_obj, '80000002')
                    attr_nullable = self._get_property_value(attr_obj, '80100033') != 'True'
                    attr_auto_inc = self._get_property_value(attr_obj, '80100035') == 'True'
                    attr_default = self._get_property_value(attr_obj, '80100034')
                    attr_order = int(self._get_property_value(attr_obj, '80400006') or 0)
                    attr_guid = self._get_property_value(attr_obj, '90000006')
                    
                    attribute = Attribute(
                        name=attr_name,
                        label=attr_label,
                        data_type=attr_type,
                        nullable=attr_nullable,
                        auto_increment=attr_auto_inc,
                        default_value=attr_default,
                        order=attr_order
                    )
                    
                    entity.attributes[attr_name] = attribute
                    self.guid_to_attribute[attr_guid] = (entity_name, attr_name)
            
            # 解析主键和索引
            for key_group in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroup']"):
                key_type = self._get_property_value(key_group, '80000097')
                key_name = self._get_property_value(key_group, '90000003')
                
                # 获取键成员
                key_members = []
                for member in key_group.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroupMember']"):
                    member_attr_id = self._get_property_value(member, '80500005')
                    # 查找对应的属性名 - 遍历所有属性对象
                    for attr_obj in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityAttribute']"):
                        attr_id = self._get_property_value(attr_obj, '90000002')
                        if attr_id == member_attr_id:
                            attr_name = self._get_property_value(attr_obj, '90000003')
                            if attr_name:
                                key_members.append(attr_name)
                            break
                
                if key_type == 'PrimaryKey':
                    entity.primary_keys = key_members
                    for attr_name in key_members:
                        if attr_name in entity.attributes:
                            entity.attributes[attr_name].is_primary_key = True
                elif key_type == 'NonUniqueKey':
                    entity.indexes[key_name] = key_members
    
    def _parse_relations(self):
        """解析实体关系（通过 RelationshipRelational）"""
        # 查找所有 RelationshipRelational
        for rel_obj in self.root.findall(".//Object[@Type='Datablau.LDM.RelationshipRelational']"):
            rel_name = self._get_property_value(rel_obj, '90000003')
            
            # 获取父实体和子实体的 ID
            parent_entity_id = self._get_property_value(rel_obj, '80000052')
            child_entity_id = self._get_property_value(rel_obj, '80000053')
            
            # 获取父键组和子键组的 ID（注意：这是 KeyGroup 的 ID，不是属性 ID）
            parent_keygroup_id = self._get_property_value(rel_obj, '80000054')
            child_keygroup_id = self._get_property_value(rel_obj, '80000055')
            
            # 获取基数
            parent_cardinality = self._get_property_value(rel_obj, '80000071')
            child_cardinality = self._get_property_value(rel_obj, '80000072')
            
            # 通过 KeyGroup 查找实际的属性 ID
            parent_attr_id = self._get_attr_from_keygroup(parent_keygroup_id)
            child_attr_id = self._get_attr_from_keygroup(child_keygroup_id)
            
            # 查找实体和属性名称
            parent_entity = None
            child_entity = None
            parent_col = None
            child_col = None
            
            for entity_obj in self.root.findall(".//Object[@Type='Datablau.LDM.EntityComposite']"):
                entity_id = self._get_property_value(entity_obj, '90000002')
                entity_name = self._get_property_value(entity_obj, '90000003')
                
                if entity_id == parent_entity_id:
                    parent_entity = entity_name
                    # 查找父键列
                    if parent_attr_id:
                        for attr_obj in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityAttribute']"):
                            attr_id = self._get_property_value(attr_obj, '90000002')
                            if attr_id == parent_attr_id:
                                parent_col = self._get_property_value(attr_obj, '90000003')
                                break
                
                if entity_id == child_entity_id:
                    child_entity = entity_name
                    # 查找子键列
                    if child_attr_id:
                        for attr_obj in entity_obj.findall(".//Object[@Type='Datablau.LDM.EntityAttribute']"):
                            attr_id = self._get_property_value(attr_obj, '90000002')
                            if attr_id == child_attr_id:
                                child_col = self._get_property_value(attr_obj, '90000003')
                                break
            
            # 创建外键关系
            if parent_entity and child_entity and parent_col and child_col:
                # 确定关系类型
                relationship = "many_to_one"
                if child_cardinality == "ZeroOneOrMore" and parent_cardinality == "ZeroOrOne":
                    relationship = "many_to_one"
                elif child_cardinality == "ZeroOrOne" and parent_cardinality == "ZeroOneOrMore":
                    relationship = "one_to_many"
                
                fk = ForeignKey(
                    name=rel_name,
                    local_column=child_col,
                    foreign_entity=parent_entity,
                    foreign_column=parent_col,
                    relationship=relationship
                )
                
                if child_entity in self.entities:
                    self.entities[child_entity].foreign_keys[rel_name] = fk
                    
                    # 标记为外键
                    if child_col in self.entities[child_entity].attributes:
                        self.entities[child_entity].attributes[child_col].is_foreign_key = True
    
    def _get_attr_from_keygroup(self, keygroup_id: str) -> Optional[str]:
        """从 KeyGroup ID 获取第一个属性 ID"""
        if not keygroup_id:
            return None
        
        # 查找 KeyGroup
        for keygroup_obj in self.root.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroup']"):
            kg_id = self._get_property_value(keygroup_obj, '90000002')
            if kg_id == keygroup_id:
                # 查找第一个成员
                for member in keygroup_obj.findall(".//Object[@Type='Datablau.LDM.EntityKeyGroupMember']"):
                    attr_ref = self._get_property_value(member, '80500005')
                    if attr_ref:
                        return attr_ref
        return None


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
        print(f"  外键数: {len(entity.foreign_keys)}")
        print(f"  索引数: {len(entity.indexes)}")


if __name__ == "__main__":
    main()
