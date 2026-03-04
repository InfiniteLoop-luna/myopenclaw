"""
osm_generator.py - 生成 OSM (Ontology-Lite Semantic Model) YAML

从解析的 DDM 实体生成四层 OSM 结构：
1. Ontology Layer - 语义真相层
2. Semantic Model Layer - 数据映射层
3. KPI Layer - 业务指标层
4. Governance Layer - 治理层
"""
import yaml
from typing import Dict, List
from ddm_parser import Entity, Attribute, ForeignKey


class OSMGenerator:
    """OSM YAML 生成器"""
    
    def __init__(self, entities: Dict[str, Entity], database_name: str = "database"):
        self.entities = entities
        self.database_name = database_name
        self.osm = {
            'ontology': {'entities': {}},
            'semantic_models': {},
            'join_graph': {'nodes': [], 'edges': []},
            'kpis': {},
            'governance': {'rules': [], 'policies': {}}
        }
    
    def generate(self) -> dict:
        """生成完整的 OSM 结构"""
        self._generate_ontology_layer()
        self._generate_semantic_model_layer()
        self._generate_join_graph()
        self._generate_kpi_layer()
        self._generate_governance_layer()
        return self.osm
    
    def _map_data_type(self, physical_type: str) -> str:
        """映射物理类型到语义类型"""
        physical_type_upper = physical_type.upper()
        
        if 'INT' in physical_type_upper:
            return 'integer'
        elif 'DECIMAL' in physical_type_upper or 'NUMERIC' in physical_type_upper or 'FLOAT' in physical_type_upper or 'DOUBLE' in physical_type_upper:
            return 'decimal'
        elif 'CHAR' in physical_type_upper or 'TEXT' in physical_type_upper:
            return 'string'
        elif 'DATE' in physical_type_upper or 'TIME' in physical_type_upper:
            return 'datetime'
        elif 'BOOL' in physical_type_upper:
            return 'boolean'
        elif 'GEOMETRY' in physical_type_upper or 'POINT' in physical_type_upper:
            return 'geometry'
        else:
            return 'string'
    
    def _infer_semantic_type(self, attr: Attribute) -> str:
        """推断语义类型"""
        name_lower = attr.name.lower()
        
        if attr.is_primary_key:
            return 'identifier'
        elif 'id' in name_lower and attr.is_foreign_key:
            return 'foreign_key'
        elif 'name' in name_lower or 'title' in name_lower:
            return 'name'
        elif 'email' in name_lower:
            return 'email'
        elif 'phone' in name_lower or 'tel' in name_lower:
            return 'phone'
        elif 'date' in name_lower or 'time' in name_lower:
            return 'timestamp'
        elif 'amount' in name_lower or 'price' in name_lower or 'cost' in name_lower:
            return 'currency'
        elif 'rate' in name_lower or 'percent' in name_lower:
            return 'percentage'
        elif 'status' in name_lower or 'state' in name_lower:
            return 'status'
        elif 'count' in name_lower or 'number' in name_lower:
            return 'count'
        else:
            return 'attribute'
    
    def _generate_ontology_layer(self):
        """生成 Ontology Layer"""
        for entity_name, entity in self.entities.items():
            # 实体名转为 PascalCase
            entity_key = self._to_pascal_case(entity_name)
            
            ontology_entity = {
                'label': entity.label,
                'description': f'{entity.label}',
                'attributes': {},
                'relations': []
            }
            
            # 添加属性
            for attr_name, attr in sorted(entity.attributes.items(), key=lambda x: x[1].order):
                ontology_entity['attributes'][attr_name] = {
                    'label': attr.label,
                    'type': self._map_data_type(attr.data_type),
                    'physical_type': attr.data_type,
                    'nullable': attr.nullable,
                    'semantic_type': self._infer_semantic_type(attr)
                }
                
                if attr.auto_increment:
                    ontology_entity['attributes'][attr_name]['auto_increment'] = True
                
                if attr.default_value:
                    ontology_entity['attributes'][attr_name]['default'] = attr.default_value
            
            # 添加关系
            for fk_name, fk in entity.foreign_keys.items():
                relation = {
                    'name': fk_name,
                    'target': self._to_pascal_case(fk.foreign_entity),
                    'cardinality': fk.relationship,
                    'inverse': f'{entity_name}s'  # 反向关系名
                }
                ontology_entity['relations'].append(relation)
            
            self.osm['ontology']['entities'][entity_key] = ontology_entity
    
    def _generate_semantic_model_layer(self):
        """生成 Semantic Model Layer"""
        for entity_name, entity in self.entities.items():
            model_id = entity_name.lower()
            entity_key = self._to_pascal_case(entity_name)
            
            semantic_model = {
                'entity': entity_key,
                'data_source': {
                    'type': 'mysql',
                    'connection': self.database_name
                },
                'table': entity.table_name,
                'primary_key': entity.primary_keys[0] if entity.primary_keys else None,
                'dimensions': {},
                'measures': {},
                'joins': {}
            }
            
            # 添加维度和度量
            for attr_name, attr in entity.attributes.items():
                semantic_type = self._infer_semantic_type(attr)
                
                # 数值类型作为度量，其他作为维度
                if attr.data_type.upper().startswith(('DECIMAL', 'NUMERIC', 'FLOAT', 'DOUBLE', 'INT', 'SMALLINT', 'BIGINT', 'TINYINT')) and not attr.is_primary_key and not attr.is_foreign_key:
                    # 度量
                    semantic_model['measures'][attr_name] = {
                        'label': attr.label,
                        'column': attr_name,
                        'aggregation': 'sum',
                        'type': self._map_data_type(attr.data_type)
                    }
                else:
                    # 维度
                    semantic_model['dimensions'][attr_name] = {
                        'label': attr.label,
                        'column': attr_name,
                        'type': self._map_data_type(attr.data_type)
                    }
            
            # 添加 joins
            for fk_name, fk in entity.foreign_keys.items():
                target_model = fk.foreign_entity.lower()
                join_id = f'{fk.foreign_entity.lower()}_join'
                
                semantic_model['joins'][join_id] = {
                    'target_model': target_model,
                    'relationship': fk.relationship,
                    'join_type': 'left',
                    'condition': {
                        'type': 'key',
                        'local_key': fk.local_column,
                        'foreign_key': fk.foreign_column
                    },
                    'required': False
                }
            
            self.osm['semantic_models'][model_id] = semantic_model
    
    def _generate_join_graph(self):
        """生成 Join Graph"""
        # 添加所有节点
        self.osm['join_graph']['nodes'] = list(self.osm['semantic_models'].keys())
        
        # 添加边
        for model_id, model in self.osm['semantic_models'].items():
            for join_id, join_def in model.get('joins', {}).items():
                edge = {
                    'from': model_id,
                    'to': join_def['target_model'],
                    'join_id': join_id
                }
                self.osm['join_graph']['edges'].append(edge)
    
    def _generate_kpi_layer(self):
        """生成基础 KPI Layer"""
        # 为每个实体生成一个基础的 count KPI
        for entity_name, entity in self.entities.items():
            model_id = entity_name.lower()
            entity_key = self._to_pascal_case(entity_name)
            kpi_id = f'{entity_name.lower()}_count'
            
            # 查找时间字段
            time_field = None
            for attr_name, attr in entity.attributes.items():
                if 'date' in attr_name.lower() or 'time' in attr_name.lower():
                    time_field = attr_name
                    break
            
            if time_field:
                kpi = {
                    'name': f'{entity.label}数量',
                    'description': f'统计{entity.label}的数量',
                    'host': {
                        'entity': entity_key,
                        'cardinality': 'many',
                        'grain': 'entity'
                    },
                    'computation': {
                        'type': 'aggregation',
                        'base_model': model_id,
                        'measure': 'count',
                        'aggregation': 'count',
                        'filters': [],
                        'joins': []
                    },
                    'time': {
                        'dimension': time_field,
                        'grain': ['day', 'week', 'month', 'year'],
                        'default_grain': 'month'
                    },
                    'output': {
                        'type': 'vector',
                        'format': 'integer'
                    }
                }
                
                self.osm['kpis'][kpi_id] = kpi
    
    def _generate_governance_layer(self):
        """生成基础 Governance Layer"""
        # 添加基础规则
        self.osm['governance']['rules'] = [
            {
                'id': 'require_time_dimension',
                'condition': 'kpi.time.dimension is not None',
                'action': 'enforce_time_dimension',
                'description': '所有 KPI 必须指定时间维度'
            }
        ]
        
        # 添加基础权限策略
        self.osm['governance']['policies'] = {
            'role_permissions': {
                'admin': {
                    'allowed_kpis': ['*'],
                    'allowed_entities': ['*']
                },
                'analyst': {
                    'allowed_kpis': list(self.osm['kpis'].keys()),
                    'allowed_entities': list(self.osm['ontology']['entities'].keys())
                }
            }
        }
    
    def _to_pascal_case(self, snake_str: str) -> str:
        """转换为 PascalCase"""
        return ''.join(word.capitalize() for word in snake_str.split('_'))
    
    def save_yaml(self, output_path: str):
        """保存为 YAML 文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            # 添加文件头注释
            f.write(f"# ============================================================\n")
            f.write(f"# OSM (Ontology-Lite Semantic Model)\n")
            f.write(f"# Auto-generated from DDM\n")
            f.write(f"# Database: {self.database_name}\n")
            f.write(f"# ============================================================\n\n")
            
            yaml.dump(self.osm, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)


def main():
    """测试生成器"""
    import sys
    from ddm_parser import DDMParser
    
    if len(sys.argv) < 3:
        print("Usage: python osm_generator.py <ddm_file> <output_yaml> [database_name]")
        sys.exit(1)
    
    ddm_file = sys.argv[1]
    output_file = sys.argv[2]
    database_name = sys.argv[3] if len(sys.argv) > 3 else "database"
    
    # 解析 DDM
    print(f"解析 DDM 文件: {ddm_file}")
    parser = DDMParser(ddm_file)
    entities = parser.parse()
    print(f"解析到 {len(entities)} 个实体")
    
    # 生成 OSM
    print(f"生成 OSM 模型...")
    generator = OSMGenerator(entities, database_name)
    osm = generator.generate()
    
    # 保存 YAML
    print(f"保存到: {output_file}")
    generator.save_yaml(output_file)
    print("完成！")


if __name__ == "__main__":
    main()
