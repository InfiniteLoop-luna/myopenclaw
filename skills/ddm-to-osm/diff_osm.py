#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diff_osm.py

比较两个 OSM YAML，输出结构化差异报告。

关注：
- meta 关键字段
- ontology entities/relations/attributes
- semantic_models
- join_graph edges
- kpis

用法：
python diff_osm.py <old_osm.yaml> <new_osm.yaml> [--md report.md] [--json report.json]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

if sys.platform == "win32":
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


def sha_obj(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def map_diff_keys(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    ak = set(a.keys())
    bk = set(b.keys())
    added = sorted(bk - ak)
    removed = sorted(ak - bk)
    common = sorted(ak & bk)
    changed = [k for k in common if sha_obj(a[k]) != sha_obj(b[k])]
    return added, removed, changed


def diff_list_as_set(a: List[Any], b: List[Any]) -> Tuple[List[Any], List[Any]]:
    sa = set(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in a)
    sb = set(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in b)
    added = [json.loads(x) for x in sorted(sb - sa)]
    removed = [json.loads(x) for x in sorted(sa - sb)]
    return added, removed


def build_diff(old_doc: Dict[str, Any], new_doc: Dict[str, Any]) -> Dict[str, Any]:
    old_meta = old_doc.get("meta") or {}
    new_meta = new_doc.get("meta") or {}

    old_ents = ((old_doc.get("ontology") or {}).get("entities") or {})
    new_ents = ((new_doc.get("ontology") or {}).get("entities") or {})

    old_models = old_doc.get("semantic_models") or {}
    new_models = new_doc.get("semantic_models") or {}

    old_kpis = old_doc.get("kpis") or {}
    new_kpis = new_doc.get("kpis") or {}

    old_edges = ((old_doc.get("join_graph") or {}).get("edges") or [])
    new_edges = ((new_doc.get("join_graph") or {}).get("edges") or [])

    ent_added, ent_removed, ent_changed = map_diff_keys(old_ents, new_ents)
    model_added, model_removed, model_changed = map_diff_keys(old_models, new_models)
    kpi_added, kpi_removed, kpi_changed = map_diff_keys(old_kpis, new_kpis)
    edge_added, edge_removed = diff_list_as_set(old_edges, new_edges)

    # 深一点：entity 的 attributes/relations 变化计数
    entity_deep: Dict[str, Any] = {}
    for e in ent_changed:
        oe = old_ents.get(e) or {}
        ne = new_ents.get(e) or {}
        oa = oe.get("attributes") or {}
        na = ne.get("attributes") or {}
        orr = oe.get("relations") or []
        nrr = ne.get("relations") or []
        a_add, a_rem, a_chg = map_diff_keys(oa, na)
        r_add, r_rem = diff_list_as_set(orr, nrr)
        entity_deep[e] = {
            "attributes": {
                "added": a_add,
                "removed": a_rem,
                "changed": a_chg,
            },
            "relations": {
                "added_count": len(r_add),
                "removed_count": len(r_rem),
            },
        }

    # kpi 依赖变化概览
    kpi_dependency_changed: List[str] = []
    for kid in kpi_changed:
        ok = old_kpis.get(kid) or {}
        nk = new_kpis.get(kid) or {}
        if sha_obj(ok.get("dependencies") or {}) != sha_obj(nk.get("dependencies") or {}):
            kpi_dependency_changed.append(kid)

    diff = {
        "summary": {
            "entities": {
                "old": len(old_ents),
                "new": len(new_ents),
                "added": len(ent_added),
                "removed": len(ent_removed),
                "changed": len(ent_changed),
            },
            "semantic_models": {
                "old": len(old_models),
                "new": len(new_models),
                "added": len(model_added),
                "removed": len(model_removed),
                "changed": len(model_changed),
            },
            "join_edges": {
                "old": len(old_edges),
                "new": len(new_edges),
                "added": len(edge_added),
                "removed": len(edge_removed),
            },
            "kpis": {
                "old": len(old_kpis),
                "new": len(new_kpis),
                "added": len(kpi_added),
                "removed": len(kpi_removed),
                "changed": len(kpi_changed),
            },
        },
        "meta": {
            "old": {
                "model_version": old_meta.get("model_version"),
                "source_fingerprint": old_meta.get("source_fingerprint"),
                "kpi_mode": old_meta.get("kpi_mode"),
            },
            "new": {
                "model_version": new_meta.get("model_version"),
                "source_fingerprint": new_meta.get("source_fingerprint"),
                "kpi_mode": new_meta.get("kpi_mode"),
            },
        },
        "details": {
            "entities": {
                "added": ent_added,
                "removed": ent_removed,
                "changed": ent_changed,
                "deep": entity_deep,
            },
            "semantic_models": {
                "added": model_added,
                "removed": model_removed,
                "changed": model_changed,
            },
            "join_edges": {
                "added": edge_added,
                "removed": edge_removed,
            },
            "kpis": {
                "added": kpi_added,
                "removed": kpi_removed,
                "changed": kpi_changed,
                "dependencies_changed": sorted(kpi_dependency_changed),
            },
        },
    }
    return diff


def render_md(diff: Dict[str, Any], old_path: str, new_path: str) -> str:
    s = diff["summary"]
    lines: List[str] = []
    lines.append("# OSM Diff Report")
    lines.append("")
    lines.append(f"- Old: `{old_path}`")
    lines.append(f"- New: `{new_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Section | Old | New | Added | Removed | Changed |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for sec in ["entities", "semantic_models", "join_edges", "kpis"]:
        x = s[sec]
        lines.append(f"| {sec} | {x['old']} | {x['new']} | {x['added']} | {x['removed']} | {x.get('changed', 0)} |")

    lines.append("")
    lines.append("## Meta")
    lines.append("")
    old_meta = diff["meta"]["old"]
    new_meta = diff["meta"]["new"]
    lines.append(f"- old.model_version: `{old_meta.get('model_version')}`")
    lines.append(f"- new.model_version: `{new_meta.get('model_version')}`")
    lines.append(f"- old.source_fingerprint: `{old_meta.get('source_fingerprint')}`")
    lines.append(f"- new.source_fingerprint: `{new_meta.get('source_fingerprint')}`")
    lines.append(f"- old.kpi_mode: `{old_meta.get('kpi_mode')}`")
    lines.append(f"- new.kpi_mode: `{new_meta.get('kpi_mode')}`")

    details = diff["details"]
    for sec in ["entities", "semantic_models", "kpis"]:
        lines.append("")
        lines.append(f"## {sec}")
        lines.append("")
        lines.append(f"- added: {len(details[sec]['added'])}")
        lines.append(f"- removed: {len(details[sec]['removed'])}")
        lines.append(f"- changed: {len(details[sec]['changed'])}")
        if details[sec]["added"]:
            lines.append(f"- added list: {details[sec]['added'][:20]}")
        if details[sec]["removed"]:
            lines.append(f"- removed list: {details[sec]['removed'][:20]}")
        if details[sec]["changed"]:
            lines.append(f"- changed list: {details[sec]['changed'][:20]}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Diff two OSM YAML files")
    parser.add_argument("old_osm", help="旧 OSM YAML")
    parser.add_argument("new_osm", help="新 OSM YAML")
    parser.add_argument("--md", default="", help="输出 Markdown 报告路径")
    parser.add_argument("--json", default="", help="输出 JSON 报告路径")
    args = parser.parse_args()

    old_path = Path(args.old_osm)
    new_path = Path(args.new_osm)

    if not old_path.exists() or not new_path.exists():
        print("❌ 输入文件不存在")
        sys.exit(2)

    with old_path.open("r", encoding="utf-8") as f:
        old_doc = yaml.safe_load(f) or {}
    with new_path.open("r", encoding="utf-8") as f:
        new_doc = yaml.safe_load(f) or {}

    diff = build_diff(old_doc, new_doc)

    print("=== OSM Diff Summary ===")
    for sec, x in diff["summary"].items():
        print(f"- {sec}: old={x['old']} new={x['new']} added={x['added']} removed={x['removed']} changed={x.get('changed',0)}")

    if args.json:
        Path(args.json).write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"🧾 JSON 报告: {args.json}")

    if args.md:
        md = render_md(diff, str(old_path), str(new_path))
        Path(args.md).write_text(md, encoding="utf-8")
        print(f"📝 Markdown 报告: {args.md}")


if __name__ == "__main__":
    main()
