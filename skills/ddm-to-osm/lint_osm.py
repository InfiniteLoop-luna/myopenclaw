#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lint_osm.py

轻量 OSM 一致性检查（P1）：
- 引用完整性（join/relations/kpi dependencies）
- governance.role_permissions 与 kpis 一致性
- KPI 标准字段完整性（host/computation/time/constraints/dependencies）

用法：
python lint_osm.py <osm_yaml> [--strict]
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

if sys.platform == "win32":
    # 避免重复包装导致 stdout/stderr 底层 buffer 被提前关闭
    for _name in ("stdout", "stderr"):
        _stream = getattr(sys, _name, None)
        _enc = (getattr(_stream, "encoding", "") or "").lower()
        if _enc.startswith("utf-8"):
            continue
        if hasattr(_stream, "buffer"):
            try:
                setattr(sys, _name, io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"))
            except Exception:
                pass


class LintResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def err(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)


def lint_osm(doc: Dict[str, Any], strict: bool = False) -> LintResult:
    r = LintResult()

    ontology_entities = ((doc.get("ontology") or {}).get("entities") or {})
    semantic_models = doc.get("semantic_models") or {}
    join_edges = ((doc.get("join_graph") or {}).get("edges") or [])
    kpis = doc.get("kpis") or {}
    policies = ((doc.get("governance") or {}).get("policies") or {})

    # 1) semantic model -> ontology entity
    for model_id, m in semantic_models.items():
        e = m.get("entity")
        if not e or e not in ontology_entities:
            r.err(f"semantic_models.{model_id}.entity 引用不存在: {e}")

    # 2) join_graph edge refs
    model_ids = set(semantic_models.keys())
    for i, edge in enumerate(join_edges, 1):
        f = edge.get("from")
        t = edge.get("to")
        if f not in model_ids:
            r.err(f"join_graph.edges[{i}] from 不存在: {f}")
        if t not in model_ids:
            r.err(f"join_graph.edges[{i}] to 不存在: {t}")

    # 3) ontology relation target refs
    for ename, edef in ontology_entities.items():
        for rel in (edef.get("relations") or []):
            target = rel.get("target")
            if target and target not in ontology_entities:
                r.err(f"ontology.entities.{ename}.relations target 不存在: {target}")

    # 4) KPI 标准字段
    for kid, k in kpis.items():
        host = k.get("host") or {}
        comp = k.get("computation") or {}
        time = k.get("time") or {}
        cons = k.get("constraints") or {}
        deps = k.get("dependencies") or {}

        for required in ["entity", "cardinality", "grain"]:
            if required not in host:
                r.err(f"kpis.{kid}.host 缺少字段: {required}")

        if "type" not in comp:
            r.err(f"kpis.{kid}.computation 缺少字段: type")

        for required in ["dimension", "default_grain", "allowed_grains", "window"]:
            if required not in time:
                r.err(f"kpis.{kid}.time 缺少字段: {required}")

        for required in ["require_time", "require_host", "allowed_filters"]:
            if required not in cons:
                r.warn(f"kpis.{kid}.constraints 缺少字段: {required}")

        for required in ["metrics", "entities"]:
            if required not in deps:
                r.warn(f"kpis.{kid}.dependencies 缺少字段: {required}")

        ctype = comp.get("type")
        if ctype == "aggregation":
            bm = comp.get("base_model")
            if bm and bm not in semantic_models:
                r.err(f"kpis.{kid}.computation.base_model 引用不存在: {bm}")
        elif ctype == "period_compare":
            bk = comp.get("base_kpi")
            if bk and bk not in kpis:
                r.err(f"kpis.{kid}.computation.base_kpi 引用不存在: {bk}")

        # dependencies.metrics ref check
        for dep in deps.get("metrics") or []:
            if dep not in kpis:
                r.warn(f"kpis.{kid}.dependencies.metrics 引用不存在: {dep}")

    # 5) governance.role_permissions allowed_kpis consistency
    role_permissions = policies.get("role_permissions") or {}
    if isinstance(role_permissions, dict):
        kpi_ids = set(kpis.keys())
        for role, perm in role_permissions.items():
            if not isinstance(perm, dict):
                continue
            allowed = perm.get("allowed_kpis")
            if isinstance(allowed, list) and "*" not in allowed:
                missing = [x for x in allowed if x not in kpi_ids]
                if missing:
                    msg = f"governance.policies.role_permissions.{role}.allowed_kpis 存在无效引用: {missing[:8]}"
                    if strict:
                        r.err(msg)
                    else:
                        r.warn(msg)

    return r


def main():
    parser = argparse.ArgumentParser(description="Lint OSM YAML")
    parser.add_argument("osm_yaml", help="OSM YAML 文件")
    parser.add_argument("--strict", action="store_true", help="将部分 warning 提升为 error")
    args = parser.parse_args()

    p = Path(args.osm_yaml)
    if not p.exists():
        print(f"❌ 文件不存在: {p}")
        sys.exit(2)

    with p.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}

    result = lint_osm(doc, strict=args.strict)

    print("\n=== OSM Lint Result ===")
    print(f"Errors  : {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")

    if result.errors:
        print("\n[Errors]")
        for e in result.errors:
            print("-", e)

    if result.warnings:
        print("\n[Warnings]")
        for w in result.warnings:
            print("-", w)

    if result.errors:
        print("\n❌ Lint failed")
        sys.exit(1)

    print("\n✅ Lint passed")


if __name__ == "__main__":
    main()
