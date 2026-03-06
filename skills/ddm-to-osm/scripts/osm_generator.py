"""
osm_generator.py - 生成 OSM (Ontology-Lite Semantic Model) YAML

从解析的 DDM 实体生成四层 OSM 结构：
1. Ontology Layer - 语义真相层
2. Semantic Model Layer - 数据映射层
3. KPI Layer - 业务指标层
4. Governance Layer - 治理层
"""

from __future__ import annotations

from datetime import datetime, timezone
import copy
import re
from typing import Dict, List, Optional, Any

import yaml

from ddm_parser import Entity, Attribute


class OSMGenerator:
    """OSM YAML 生成器"""

    def __init__(
        self,
        entities: Dict[str, Entity],
        database_name: str = "database",
        kpi_mode: str = "advanced",  # basic | advanced
        profile: Optional[Dict[str, Any]] = None,
        source_name: Optional[str] = None,
        generator_version: str = "1.2.0-p1",
    ):
        self.entities = entities
        self.database_name = database_name
        self.kpi_mode = (kpi_mode or "advanced").lower()
        if self.kpi_mode not in {"basic", "advanced"}:
            self.kpi_mode = "advanced"

        self.profile = profile or {}
        self.source_name = source_name
        self.generator_version = generator_version

        self.ontology_rules = self.profile.get("ontology_rules", {}) if isinstance(self.profile, dict) else {}
        self.semantic_rules = self.profile.get("semantic_rules", {}) if isinstance(self.profile, dict) else {}

        self.allowed_grains = ["day", "week", "month", "quarter", "year"]

        self.osm = {
            "meta": {},
            "ontology": {"entities": {}},
            "semantic_models": {},
            "join_graph": {"nodes": [], "edges": []},
            "kpis": {},
            "governance": {"rules": [], "policies": {}},
        }

    # ----------------------------
    # public
    # ----------------------------

    def generate(self) -> dict:
        """生成完整的 OSM 结构"""
        self._generate_meta()
        self._generate_ontology_layer()
        self._generate_semantic_model_layer()
        self._generate_join_graph()
        self._generate_kpi_layer()
        self._generate_governance_layer()
        return self.osm

    def save_yaml(self, output_path: str):
        """保存为 YAML 文件"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# ============================================================\n")
            f.write("# OSM (Ontology-Lite Semantic Model)\n")
            f.write("# Auto-generated from DDM\n")
            f.write(f"# Database: {self.database_name}\n")
            f.write("# ============================================================\n\n")
            yaml.dump(self.osm, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)

    # ----------------------------
    # meta
    # ----------------------------

    def _generate_meta(self):
        ds_cfg = self.profile.get("data_source", {}) if isinstance(self.profile, dict) else {}
        self.osm["meta"] = {
            "schema_version": "osm-v1.0",
            "generator": "ddm-to-osm",
            "generator_version": self.generator_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kpi_mode": self.kpi_mode,
            "source": {
                "ddm": self.source_name,
                "database": self.database_name,
            },
            "summary": {
                "entity_count": len(self.entities),
                "data_source_type": ds_cfg.get("type", "mysql"),
            },
        }

    # ----------------------------
    # common utils
    # ----------------------------

    @staticmethod
    def _deep_merge(a: Any, b: Any) -> Any:
        """深度合并（b 覆盖 a）"""
        if isinstance(a, dict) and isinstance(b, dict):
            out = copy.deepcopy(a)
            for k, v in b.items():
                if k in out:
                    out[k] = OSMGenerator._deep_merge(out[k], v)
                else:
                    out[k] = copy.deepcopy(v)
            return out
        return copy.deepcopy(b)

    def _map_data_type(self, physical_type: str) -> str:
        """映射物理类型到语义类型"""
        t = (physical_type or "").upper()
        if "INT" in t:
            return "integer"
        if any(x in t for x in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE"]):
            return "decimal"
        if any(x in t for x in ["CHAR", "TEXT"]):
            return "string"
        if any(x in t for x in ["DATE", "TIME"]):
            return "datetime"
        if "BOOL" in t:
            return "boolean"
        if any(x in t for x in ["GEOMETRY", "POINT"]):
            return "geometry"
        return "string"

    def _infer_semantic_type(self, attr: Attribute) -> str:
        """
        推断语义类型（边界匹配，减少 substring 误判，如 country -> count）
        """
        name = (attr.name or "").lower()

        if attr.is_primary_key:
            return "identifier"

        if attr.is_foreign_key and re.search(r"(?:^|_)id$", name):
            return "foreign_key"

        if re.search(r"(?:^|_)(name|title)(?:_|$)", name):
            return "name"
        if re.search(r"(?:^|_)(email|mail)(?:_|$)", name):
            return "email"
        if re.search(r"(?:^|_)(phone|tel|mobile)(?:_|$)", name):
            return "phone"
        if re.search(r"(?:^|_)(date|time|timestamp|created_at|updated_at)(?:_|$)", name):
            return "timestamp"
        if re.search(r"(?:^|_)(amount|price|cost|fee|revenue|income)(?:_|$)", name):
            return "currency"
        if re.search(r"(?:^|_)(rate|ratio|percent|pct)(?:_|$)", name):
            return "percentage"
        if re.search(r"(?:^|_)(status|state)(?:_|$)", name):
            return "status"
        if re.search(r"(?:^|_)(count|cnt|number|num|qty|quantity|volume)(?:_|$)", name):
            return "count"

        return "attribute"

    @staticmethod
    def _to_pascal_case(snake_str: str) -> str:
        return "".join(word.capitalize() for word in (snake_str or "").split("_"))

    @staticmethod
    def _pluralize(word: str) -> str:
        """简易英文复数规则（修复 city->cities / address->addresses）"""
        if not word:
            return word
        w = word.strip()
        lw = w.lower()
        if lw.endswith(("s", "x", "z", "ch", "sh")):
            return w + "es"
        if len(w) > 1 and lw.endswith("y") and lw[-2] not in "aeiou":
            return w[:-1] + "ies"
        return w + "s"

    @staticmethod
    def _safe_id(text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_]+", "_", text or "")
        s = re.sub(r"_+", "_", s).strip("_")
        return s.lower() or "id"

    def _new_time_block(self, dimension: Optional[str]) -> dict:
        """统一 KPI time 结构：dimension/default_grain/allowed_grains/window"""
        return {
            "dimension": dimension or None,
            "default_grain": "month",
            "allowed_grains": list(self.allowed_grains),
            "window": None,
        }

    def _get_entity_rule(self, entity_name: str, entity_key: str) -> Dict[str, Any]:
        """读取 profile 中某实体的 ontology 规则"""
        entities_rules = (self.ontology_rules or {}).get("entities", {})
        if not isinstance(entities_rules, dict):
            return {}
        return (
            entities_rules.get(entity_key)
            or entities_rules.get(entity_name)
            or entities_rules.get(entity_name.lower())
            or {}
        )

    # ----------------------------
    # Ontology
    # ----------------------------

    def _build_auto_constraints(self, entity_name: str, entity_key: str, entity: Entity) -> List[dict]:
        constraints: List[dict] = []

        # PK unique
        if entity.primary_keys:
            pk_expr = ", ".join(entity.primary_keys)
            constraints.append(
                {
                    "type": "unique",
                    "rule": f"{entity_key}.{pk_expr} must be unique",
                    "source": "auto_primary_key",
                }
            )

        # unique keys
        for uk_name, cols in (entity.unique_keys or {}).items():
            if not cols:
                continue
            constraints.append(
                {
                    "type": "unique",
                    "rule": f"{entity_key}.{', '.join(cols)} must be unique",
                    "name": uk_name,
                    "source": "auto_unique_key",
                }
            )

        # required relation（外键列都不可空）
        for fk_name, fk in (entity.foreign_keys or {}).items():
            local_cols = fk.local_columns or []
            if not local_cols:
                continue
            all_not_null = True
            for c in local_cols:
                a = entity.attributes.get(c)
                if not a or a.nullable:
                    all_not_null = False
                    break
            if all_not_null:
                constraints.append(
                    {
                        "type": "required_relation",
                        "rule": f"{entity_key} must relate to {self._to_pascal_case(fk.foreign_entity)} via ({', '.join(local_cols)})",
                        "relation": fk_name,
                        "source": "auto_required_fk",
                    }
                )

        # range template（保守）
        for attr_name, attr in entity.attributes.items():
            sem = self._infer_semantic_type(attr)
            an = attr_name.lower()
            if an == "age" and self._map_data_type(attr.data_type) in {"integer", "decimal"}:
                constraints.append(
                    {
                        "type": "range",
                        "rule": f"{entity_key}.{attr_name} must be between 0 and 150",
                        "source": "auto_range",
                    }
                )
            elif sem == "percentage":
                constraints.append(
                    {
                        "type": "range",
                        "rule": f"{entity_key}.{attr_name} must be between 0 and 100",
                        "source": "auto_range",
                    }
                )

        return constraints

    def _build_auto_enums(self, entity: Entity) -> Dict[str, list]:
        enums: Dict[str, list] = {}
        for attr_name, attr in entity.attributes.items():
            mapped = self._map_data_type(attr.data_type)
            n = attr_name.lower()
            if mapped == "boolean":
                enums[attr_name] = [True, False]
            elif mapped == "integer" and n in {"active", "enabled", "disabled", "is_active", "is_deleted"}:
                enums[attr_name] = [0, 1]
        return enums

    def _generate_ontology_layer(self):
        for entity_name, entity in self.entities.items():
            entity_key = self._to_pascal_case(entity_name)
            entity_rule = self._get_entity_rule(entity_name, entity_key)

            ontology_entity = {
                "label": entity.label,
                "description": f"{entity.label}",
                "attributes": {},
                "relations": [],
                "constraints": [],
                "enums": {},
            }

            # 属性
            for attr_name, attr in sorted(entity.attributes.items(), key=lambda x: x[1].order):
                attr_obj = {
                    "label": attr.label,
                    "type": self._map_data_type(attr.data_type),
                    "physical_type": attr.data_type,
                    "nullable": attr.nullable,
                    "semantic_type": self._infer_semantic_type(attr),
                }
                if attr.auto_increment:
                    attr_obj["auto_increment"] = True
                if attr.default_value:
                    attr_obj["default"] = attr.default_value
                ontology_entity["attributes"][attr_name] = attr_obj

            # 关系
            for fk_name, fk in entity.foreign_keys.items():
                relation = {
                    "name": fk_name,
                    "target": self._to_pascal_case(fk.foreign_entity),
                    "cardinality": fk.relationship,
                    "inverse": self._pluralize(entity_name),
                }
                if len(fk.local_columns) > 1:
                    relation["joiner"] = "columns"
                ontology_entity["relations"].append(relation)

            # 自动 constraints
            constraints = self._build_auto_constraints(entity_name, entity_key, entity)

            # profile constraints
            profile_constraints = entity_rule.get("constraints", [])
            if isinstance(profile_constraints, list):
                constraints.extend(profile_constraints)

            ontology_entity["constraints"] = constraints

            # 自动 enums
            enums = self._build_auto_enums(entity)

            # profile enums
            profile_enums = entity_rule.get("enums", {})
            if isinstance(profile_enums, dict):
                for k, v in profile_enums.items():
                    enums[k] = v

            ontology_entity["enums"] = enums

            self.osm["ontology"]["entities"][entity_key] = ontology_entity

    # ----------------------------
    # Semantic Model
    # ----------------------------

    def _auto_filters_for_model(self, entity: Entity) -> Dict[str, Any]:
        """自动生成常见静态 filter 模板（声明式，不自动启用）"""
        filters: Dict[str, Any] = {}
        attrs = entity.attributes

        # not_deleted: is_deleted = 0 / false
        for c in ["is_deleted", "deleted", "del_flag"]:
            if c in attrs:
                mapped = self._map_data_type(attrs[c].data_type)
                filters["not_deleted"] = {
                    "expression": {
                        "type": "condition",
                        "field": c,
                        "operator": "=",
                        "value": False if mapped == "boolean" else 0,
                    }
                }
                break

        # not_deleted_at: deleted_at is null
        for c in ["deleted_at", "delete_time", "removed_at"]:
            if c in attrs:
                filters["not_deleted_at"] = {
                    "expression": {
                        "type": "condition",
                        "field": c,
                        "operator": "is",
                        "value": None,
                    }
                }
                break

        # active_only
        for c in ["active", "is_active", "enabled"]:
            if c in attrs:
                mapped = self._map_data_type(attrs[c].data_type)
                filters["active_only"] = {
                    "expression": {
                        "type": "condition",
                        "field": c,
                        "operator": "=",
                        "value": True if mapped == "boolean" else 1,
                    }
                }
                break

        return filters

    def _get_model_semantic_rule(self, model_id: str, join_id: Optional[str] = None, fk_name: Optional[str] = None) -> Dict[str, Any]:
        rules = self.semantic_rules or {}
        joins = rules.get("joins", {}) if isinstance(rules, dict) else {}
        if not isinstance(joins, dict):
            return {}
        model_rules = joins.get(model_id, {})
        if not isinstance(model_rules, dict):
            return {}

        if join_id and join_id in model_rules and isinstance(model_rules[join_id], dict):
            return model_rules[join_id]
        if fk_name and fk_name in model_rules and isinstance(model_rules[fk_name], dict):
            return model_rules[fk_name]
        return {}

    def _get_model_filter_rule(self, model_id: str) -> Dict[str, Any]:
        rules = self.semantic_rules or {}
        filters = rules.get("filters", {}) if isinstance(rules, dict) else {}
        if not isinstance(filters, dict):
            return {}
        val = filters.get(model_id, {})
        return val if isinstance(val, dict) else {}

    def _generate_semantic_model_layer(self):
        ds_cfg = self.profile.get("data_source", {}) if isinstance(self.profile, dict) else {}
        ds_type = ds_cfg.get("type", "mysql")
        ds_conn = ds_cfg.get("connection", self.database_name)

        for entity_name, entity in self.entities.items():
            model_id = entity_name.lower()
            entity_key = self._to_pascal_case(entity_name)

            semantic_model = {
                "entity": entity_key,
                "data_source": {"type": ds_type, "connection": ds_conn},
                "table": entity.table_name,
                "primary_key": entity.primary_keys[0] if entity.primary_keys else None,
                "dimensions": {},
                "measures": {},
                "joins": {},
                "filters": {},
            }

            for attr_name, attr in entity.attributes.items():
                mapped_type = self._map_data_type(attr.data_type)
                is_numeric = attr.data_type.upper().startswith(
                    ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "INT", "SMALLINT", "BIGINT", "TINYINT")
                )
                if is_numeric and not attr.is_primary_key and not attr.is_foreign_key:
                    semantic_model["measures"][attr_name] = {
                        "label": attr.label,
                        "column": attr_name,
                        "aggregation": "sum",
                        "type": mapped_type,
                    }
                else:
                    semantic_model["dimensions"][attr_name] = {
                        "label": attr.label,
                        "column": attr_name,
                        "type": mapped_type,
                    }

            # joins
            used_join_ids = set()
            for fk_name, fk in entity.foreign_keys.items():
                target_model = fk.foreign_entity.lower()
                base_join_id = self._safe_id(f"{fk_name}_join")
                join_id = base_join_id
                idx = 2
                while join_id in used_join_ids:
                    join_id = f"{base_join_id}_{idx}"
                    idx += 1
                used_join_ids.add(join_id)

                cond = {"type": "key"}
                if len(fk.local_columns) == 1 and len(fk.foreign_columns) == 1:
                    cond["local_key"] = fk.local_columns[0]
                    cond["foreign_key"] = fk.foreign_columns[0]
                else:
                    cond["local_keys"] = list(fk.local_columns)
                    cond["foreign_keys"] = list(fk.foreign_columns)

                join_obj: Dict[str, Any] = {
                    "target_model": target_model,
                    "relationship": fk.relationship,
                    "join_type": "left",
                    "condition": cond,
                    "required": False,
                }
                if fk.on_delete:
                    join_obj["on_delete"] = fk.on_delete
                if fk.on_update:
                    join_obj["on_update"] = fk.on_update

            # profile 允许覆写 join（包括 expression / temporal_validity）
                join_override = self._get_model_semantic_rule(model_id, join_id=join_id, fk_name=fk_name)
                if join_override:
                    join_obj = self._deep_merge(join_obj, join_override)

                # 若 condition.type=expression，清理 key join 残留字段，避免语义歧义
                cond_type = str((join_obj.get("condition") or {}).get("type") or "").lower()
                if cond_type == "expression":
                    cond_obj = join_obj.get("condition", {})
                    cond_obj.pop("local_key", None)
                    cond_obj.pop("foreign_key", None)
                    cond_obj.pop("local_keys", None)
                    cond_obj.pop("foreign_keys", None)
                    join_obj["condition"] = cond_obj

                semantic_model["joins"][join_id] = join_obj

            # filters（自动 + profile）
            auto_filters = self._auto_filters_for_model(entity)
            semantic_model["filters"] = auto_filters

            profile_filters = self._get_model_filter_rule(model_id)
            if profile_filters:
                semantic_model["filters"] = self._deep_merge(semantic_model["filters"], profile_filters)

            self.osm["semantic_models"][model_id] = semantic_model

    # ----------------------------
    # Join graph
    # ----------------------------

    def _generate_join_graph(self):
        self.osm["join_graph"]["nodes"] = list(self.osm["semantic_models"].keys())

        for model_id, model in self.osm["semantic_models"].items():
            for join_id, join_def in model.get("joins", {}).items():
                self.osm["join_graph"]["edges"].append(
                    {
                        "from": model_id,
                        "to": join_def["target_model"],
                        "join_id": join_id,
                    }
                )

    # ----------------------------
    # KPI
    # ----------------------------

    def _generate_kpi_layer(self):
        """KPI 层：basic=stage1；advanced=stage1+stage2+stage3"""

        def find_time_field(model_def: dict) -> str:
            dims = model_def.get("dimensions", {}) or {}
            for dim_name, dim_def in dims.items():
                col = (dim_def.get("column") or dim_name).lower()
                if "date" in col or "time" in col:
                    return dim_name
            return ""

        def measure_role(measure_name: str, measure_def: dict) -> str:
            n = (measure_name or "").lower()
            lbl = str(measure_def.get("label") or "").lower()
            t = str(measure_def.get("type") or "").lower()
            text = f"{n} {lbl} {t}"

            if any(k in text for k in ["amount", "price", "cost", "revenue", "fee", "payment", "currency"]):
                return "monetary"
            if any(k in text for k in ["count", "qty", "quantity", "num", "number", "volume"]):
                return "volume"
            if any(k in text for k in ["rate", "ratio", "percent", "pct"]):
                return "rate"
            if "integer" in t or "decimal" in t:
                return "numeric"
            return "other"

        def add_kpi(kpi_id: str, kpi_def: dict):
            if kpi_id in self.osm["kpis"]:
                return
            self.osm["kpis"][kpi_id] = kpi_def

        # -------- stage 1: 基础 KPI --------
        for model_id, model_def in self.osm["semantic_models"].items():
            entity_key = model_def.get("entity", self._to_pascal_case(model_id))
            entity_label = self.osm["ontology"]["entities"].get(entity_key, {}).get("label", entity_key)
            time_field = find_time_field(model_def)

            add_kpi(
                f"{model_id}_count",
                {
                    "name": f"{entity_label}数量",
                    "description": f"统计{entity_label}记录数量",
                    "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                    "computation": {
                        "type": "aggregation",
                        "base_model": model_id,
                        "measure": "count",
                        "aggregation": "count",
                        "filters": [],
                        "joins": [],
                    },
                    "time": self._new_time_block(time_field),
                    "output": {"type": "vector", "format": "integer"},
                },
            )

            measures = model_def.get("measures", {}) or {}
            for m_name, m_def in measures.items():
                role = measure_role(m_name, m_def)
                m_label = m_def.get("label", m_name)
                m_type = (m_def.get("type") or "").lower()

                if m_type in ["integer", "decimal"] or role in ["monetary", "volume", "numeric"]:
                    add_kpi(
                        f"{model_id}_{m_name}_sum",
                        {
                            "name": f"{m_label}总计",
                            "description": f"{entity_label}的{m_label}总和",
                            "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                            "computation": {
                                "type": "aggregation",
                                "base_model": model_id,
                                "measure": m_name,
                                "aggregation": "sum",
                                "filters": [],
                                "joins": [],
                            },
                            "time": self._new_time_block(time_field),
                            "output": {"type": "vector", "format": "currency" if role == "monetary" else "number"},
                            "tags": [role, "base", "sum"],
                        },
                    )

                    add_kpi(
                        f"{model_id}_{m_name}_avg",
                        {
                            "name": f"{m_label}均值",
                            "description": f"{entity_label}的{m_label}平均值",
                            "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                            "computation": {
                                "type": "aggregation",
                                "base_model": model_id,
                                "measure": m_name,
                                "aggregation": "avg",
                                "filters": [],
                                "joins": [],
                            },
                            "time": self._new_time_block(time_field),
                            "output": {"type": "scalar", "format": "currency" if role == "monetary" else "number"},
                            "tags": [role, "base", "avg"],
                        },
                    )

                add_kpi(
                    f"{model_id}_{m_name}_max",
                    {
                        "name": f"{m_label}最大值",
                        "description": f"{entity_label}的{m_label}最大值",
                        "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                        "computation": {
                            "type": "aggregation",
                            "base_model": model_id,
                            "measure": m_name,
                            "aggregation": "max",
                            "filters": [],
                            "joins": [],
                        },
                        "time": self._new_time_block(time_field),
                        "output": {"type": "scalar", "format": "number"},
                        "tags": [role, "base", "max"],
                    },
                )

                add_kpi(
                    f"{model_id}_{m_name}_min",
                    {
                        "name": f"{m_label}最小值",
                        "description": f"{entity_label}的{m_label}最小值",
                        "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                        "computation": {
                            "type": "aggregation",
                            "base_model": model_id,
                            "measure": m_name,
                            "aggregation": "min",
                            "filters": [],
                            "joins": [],
                        },
                        "time": self._new_time_block(time_field),
                        "output": {"type": "scalar", "format": "number"},
                        "tags": [role, "base", "min"],
                    },
                )

            pk = model_def.get("primary_key")
            if pk:
                add_kpi(
                    f"{model_id}_{pk}_distinct_count",
                    {
                        "name": f"{entity_label}去重数量",
                        "description": f"{entity_label}按主键去重计数",
                        "host": {"entity": entity_key, "cardinality": "many", "grain": "entity"},
                        "computation": {
                            "type": "aggregation",
                            "base_model": model_id,
                            "measure": pk,
                            "aggregation": "count_distinct",
                            "filters": [],
                            "joins": [],
                        },
                        "time": self._new_time_block(time_field),
                        "output": {"type": "vector", "format": "integer"},
                        "tags": ["identifier", "distinct", "base"],
                    },
                )

        if self.kpi_mode == "basic":
            self._normalize_kpi_layer()
            return

        # -------- stage 2: 复合公式 KPI --------
        kpi_ids = list(self.osm["kpis"].keys())
        by_model: Dict[str, List[Any]] = {}
        for kid in kpi_ids:
            k = self.osm["kpis"][kid]
            model = (k.get("computation") or {}).get("base_model")
            if not model:
                continue
            by_model.setdefault(model, []).append((kid, k))

        for model_id, items in by_model.items():
            monetary_sum_ids = [
                kid for kid, k in items if "tags" in k and "monetary" in k["tags"] and "sum" in k["tags"]
            ]

            count_id = f"{model_id}_count"
            pk_distinct = None
            model_pk = self.osm["semantic_models"].get(model_id, {}).get("primary_key")
            if model_pk:
                pk_distinct = f"{model_id}_{model_pk}_distinct_count"

            for msid in monetary_sum_ids[:2]:
                if count_id in self.osm["kpis"]:
                    add_kpi(
                        f"{msid}_per_record",
                        {
                            "name": f"{self.osm['kpis'][msid]['name']}每记录均值",
                            "description": "复合指标：金额总计 / 记录数",
                            "host": self.osm["kpis"][msid]["host"],
                            "computation": {
                                "type": "formula",
                                "expression": f"kpi:{msid} / nullif(kpi:{count_id}, 0)",
                                "dependencies": [msid, count_id],
                            },
                            "time": self.osm["kpis"][msid]["time"],
                            "output": {"type": "scalar", "format": "currency"},
                            "tags": ["derived", "formula", "avg_ticket_like"],
                        },
                    )

                if pk_distinct and pk_distinct in self.osm["kpis"]:
                    add_kpi(
                        f"{msid}_per_entity",
                        {
                            "name": f"{self.osm['kpis'][msid]['name']}每实体均值",
                            "description": "复合指标：金额总计 / 主键去重数",
                            "host": self.osm["kpis"][msid]["host"],
                            "computation": {
                                "type": "formula",
                                "expression": f"kpi:{msid} / nullif(kpi:{pk_distinct}, 0)",
                                "dependencies": [msid, pk_distinct],
                            },
                            "time": self.osm["kpis"][msid]["time"],
                            "output": {"type": "scalar", "format": "currency"},
                            "tags": ["derived", "formula", "arpu_like"],
                        },
                    )

            if len(monetary_sum_ids) >= 2:
                a, b = monetary_sum_ids[0], monetary_sum_ids[1]
                add_kpi(
                    f"{a}_share_of_{b}",
                    {
                        "name": f"{self.osm['kpis'][a]['name']}占{self.osm['kpis'][b]['name']}比例",
                        "description": "复合指标：A / B",
                        "host": self.osm["kpis"][a]["host"],
                        "computation": {
                            "type": "formula",
                            "expression": f"kpi:{a} / nullif(kpi:{b}, 0)",
                            "dependencies": [a, b],
                        },
                        "time": self.osm["kpis"][a]["time"],
                        "output": {"type": "scalar", "format": "percentage"},
                        "tags": ["derived", "formula", "share"],
                    },
                )

        # -------- stage 3: 时序派生 KPI --------
        base_for_compare = [
            kid for kid, k in self.osm["kpis"].items() if (k.get("computation") or {}).get("type") == "aggregation"
        ]

        for kid in base_for_compare:
            k = self.osm["kpis"][kid]
            if not (k.get("time") or {}).get("dimension"):
                continue

            add_kpi(
                f"{kid}_yoy",
                {
                    "name": f"{k['name']}同比",
                    "description": "时序派生指标：同比增长率",
                    "host": k["host"],
                    "computation": {"type": "period_compare", "base_kpi": kid, "compare": "yoy"},
                    "time": k["time"],
                    "output": {"type": "scalar", "format": "percentage"},
                    "tags": ["derived", "yoy"],
                },
            )

            add_kpi(
                f"{kid}_mom",
                {
                    "name": f"{k['name']}环比",
                    "description": "时序派生指标：环比增长率",
                    "host": k["host"],
                    "computation": {"type": "period_compare", "base_kpi": kid, "compare": "mom"},
                    "time": k["time"],
                    "output": {"type": "scalar", "format": "percentage"},
                    "tags": ["derived", "mom"],
                },
            )

        self._normalize_kpi_layer()

    def _normalize_kpi_layer(self):
        """P1: 统一 KPI 结构，补齐 constraints/dependencies 等标准字段"""

        all_kpis = self.osm.get("kpis", {}) or {}
        semantic_models = self.osm.get("semantic_models", {}) or {}

        for kpi_id, kpi in all_kpis.items():
            host = kpi.setdefault("host", {})
            if not host.get("entity"):
                host["entity"] = "Unknown"
            host.setdefault("cardinality", "many")
            host.setdefault("grain", "entity")

            comp = kpi.setdefault("computation", {})
            ctype = comp.get("type", "aggregation")
            comp.setdefault("type", ctype)

            if ctype == "aggregation":
                comp.setdefault("base_model", "")
                comp.setdefault("measure", "count")
                comp.setdefault("aggregation", "count")
                comp.setdefault("filters", [])
                comp.setdefault("joins", [])
            elif ctype == "formula":
                comp.setdefault("expression", "")
                comp.setdefault("dependencies", [])
            elif ctype == "period_compare":
                comp.setdefault("base_kpi", "")
                comp.setdefault("compare", "yoy")

            # 兼容历史 time 结构并统一
            t = kpi.get("time") or {}
            if "allowed_grains" not in t and "grain" in t and isinstance(t.get("grain"), list):
                t["allowed_grains"] = t.get("grain")
            if "default_grain" not in t:
                t["default_grain"] = "month"
            if "dimension" not in t:
                t["dimension"] = None
            if "allowed_grains" not in t:
                t["allowed_grains"] = list(self.allowed_grains)
            if "window" not in t:
                t["window"] = None
            if "grain" in t:
                t.pop("grain", None)
            kpi["time"] = t

            out = kpi.setdefault("output", {})
            out.setdefault("type", "scalar")
            out.setdefault("format", "number")

            # constraints
            constraints = kpi.setdefault("constraints", {})
            if "require_time" not in constraints:
                constraints["require_time"] = bool(t.get("dimension"))
            constraints.setdefault("require_host", True)
            constraints.setdefault("allowed_filters", [])

            # dependencies（标准层字段）
            deps = kpi.setdefault("dependencies", {})
            deps_metrics = deps.get("metrics")
            deps_entities = deps.get("entities")
            if deps_metrics is None:
                if ctype == "period_compare":
                    deps_metrics = [comp.get("base_kpi")] if comp.get("base_kpi") else []
                elif ctype == "formula":
                    deps_metrics = list(comp.get("dependencies", []) or [])
                else:
                    deps_metrics = []
                deps["metrics"] = deps_metrics
            if deps_entities is None:
                deps["entities"] = [host.get("entity")] if host.get("entity") else []

            # 尝试补 allowed_filters：从 base_model 维度推一些常见值
            if not constraints.get("allowed_filters"):
                base_model = comp.get("base_model")
                if base_model and base_model in semantic_models:
                    dims = semantic_models[base_model].get("dimensions", {}) or {}
                    hints = []
                    for dim_id in dims.keys():
                        dl = dim_id.lower()
                        if any(x in dl for x in ["region", "country", "city", "store", "status", "category", "date", "time"]):
                            hints.append(dim_id)
                    constraints["allowed_filters"] = hints[:8]


    # ----------------------------
    # Governance
    # ----------------------------

    def _generate_governance_layer(self):
        self.osm["governance"]["rules"] = [
            {
                "id": "require_time_dimension",
                "condition": "kpi.time.dimension is not None",
                "action": "enforce_time_dimension",
                "description": "所有 KPI 必须指定时间维度",
            }
        ]

        self.osm["governance"]["policies"] = {
            "role_permissions": {
                "admin": {"allowed_kpis": ["*"], "allowed_entities": ["*"]},
                "analyst": {
                    "allowed_kpis": list(self.osm["kpis"].keys()),
                    "allowed_entities": list(self.osm["ontology"]["entities"].keys()),
                },
            }
        }


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

    print(f"解析 DDM 文件: {ddm_file}")
    parser = DDMParser(ddm_file)
    entities = parser.parse()
    print(f"解析到 {len(entities)} 个实体")

    print("生成 OSM 模型...")
    generator = OSMGenerator(entities, database_name)
    generator.generate()

    print(f"保存到: {output_file}")
    generator.save_yaml(output_file)
    print("完成！")


if __name__ == "__main__":
    main()
