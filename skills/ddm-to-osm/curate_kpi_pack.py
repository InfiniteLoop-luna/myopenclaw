#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
curate_kpi_pack.py

从增强版 OSM KPI 集合中自动筛选“高价值 KPI 包”（默认 Top 30）。

输入:  完整 OSM YAML（例如 sakila_generated_advanced_kpis.yaml）
输出:
  1) 过滤后的 OSM YAML（仅保留 TopN KPI）
  2) KPI 排序报告 Markdown

用法:
python curate_kpi_pack.py <input_osm_yaml> <output_osm_yaml> [--top 30] [--report report.md]
"""

from __future__ import annotations

import argparse
import copy
import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

# 兼容 Windows 控制台中文/emoji（避免重复包装导致流关闭）
if sys.platform == 'win32':
    for _name in ('stdout', 'stderr'):
        _stream = getattr(sys, _name, None)
        _enc = (getattr(_stream, 'encoding', '') or '').lower()
        if _enc.startswith('utf-8'):
            continue
        if hasattr(_stream, 'buffer'):
            try:
                setattr(sys, _name, io.TextIOWrapper(_stream.buffer, encoding='utf-8', errors='replace'))
            except Exception:
                pass


@dataclass
class KPIInfo:
    kpi_id: str
    name: str
    comp_type: str
    base_model: str
    tags: List[str]
    score: float
    reason: List[str]


def get_base_model(kpi_id: str, kpi: Dict[str, Any], kpis: Dict[str, Dict[str, Any]]) -> str:
    comp = kpi.get("computation", {}) or {}
    ctype = comp.get("type", "")

    if ctype == "aggregation":
        return comp.get("base_model", "")

    if ctype == "period_compare":
        bk = comp.get("base_kpi")
        if bk and bk in kpis:
            return get_base_model(bk, kpis[bk], kpis)

    if ctype == "formula":
        deps = comp.get("dependencies", []) or []
        for dep in deps:
            if dep in kpis:
                bm = get_base_model(dep, kpis[dep], kpis)
                if bm:
                    return bm

    # fallback: 从 id 猜 model 前缀
    if "_" in kpi_id:
        return kpi_id.split("_", 1)[0]
    return ""


def score_kpi(kpi_id: str, kpi: Dict[str, Any], kpis: Dict[str, Dict[str, Any]]) -> Tuple[float, List[str]]:
    score = 0.0
    reason: List[str] = []

    comp = kpi.get("computation", {}) or {}
    ctype = comp.get("type", "")
    tags = set(kpi.get("tags", []) or [])
    name = str(kpi.get("name", ""))

    # 1) 计算类型打分
    if ctype == "aggregation":
        score += 30
        reason.append("aggregation +30")
    elif ctype == "formula":
        score += 22
        reason.append("formula +22")
    elif ctype == "period_compare":
        score += 12
        reason.append("period_compare +12")

    # 2) 聚合函数偏好
    agg = str(comp.get("aggregation", "")).lower()
    if agg == "sum":
        score += 12
        reason.append("sum +12")
    elif agg == "count":
        score += 10
        reason.append("count +10")
    elif agg == "count_distinct":
        score += 11
        reason.append("count_distinct +11")
    elif agg == "avg":
        score += 8
        reason.append("avg +8")
    elif agg in ("max", "min"):
        score += 2
        reason.append(f"{agg} +2")

    # 3) 标签偏好（业务价值）
    if "monetary" in tags:
        score += 14
        reason.append("monetary +14")
    if "rate" in tags:
        score += 10
        reason.append("rate +10")
    if "volume" in tags:
        score += 8
        reason.append("volume +8")
    if "numeric" in tags:
        score += 6
        reason.append("numeric +6")
    if "identifier" in tags and "distinct" in tags:
        score += 8
        reason.append("identifier+distinct +8")

    # 4) 名称关键词增强
    lower_name = name.lower()
    for kw in ["总计", "收入", "销售", "金额", "支付", "转化率", "均值", "去重", "数量"]:
        if kw in name:
            score += 2
            reason.append(f"name:{kw} +2")

    # 5) 过量时序指标适度降权
    if ctype == "period_compare" or kpi_id.endswith("_yoy") or kpi_id.endswith("_mom"):
        score -= 4
        reason.append("time_compare_penalty -4")

    # 6) max/min 相对弱价值
    if agg in ("max", "min"):
        score -= 2
        reason.append("max/min penalty -2")

    # 7) 依赖可解释性加分
    deps = comp.get("dependencies", []) or []
    if deps:
        score += min(6, len(deps) * 2)
        reason.append(f"dependencies +{min(6, len(deps) * 2)}")

    # 8) 没有时间维略降（便于时序分析）
    time_dim = (kpi.get("time") or {}).get("dimension")
    if not time_dim:
        score -= 3
        reason.append("no_time_dimension -3")

    return score, reason


def build_ranked_list(kpis: Dict[str, Dict[str, Any]]) -> List[KPIInfo]:
    ranked: List[KPIInfo] = []
    for kpi_id, k in kpis.items():
        s, r = score_kpi(kpi_id, k, kpis)
        info = KPIInfo(
            kpi_id=kpi_id,
            name=str(k.get("name", kpi_id)),
            comp_type=str((k.get("computation", {}) or {}).get("type", "")),
            base_model=get_base_model(kpi_id, k, kpis),
            tags=list(k.get("tags", []) or []),
            score=s,
            reason=r,
        )
        ranked.append(info)
    ranked.sort(key=lambda x: x.score, reverse=True)
    return ranked


def select_top_kpis(kpis: Dict[str, Dict[str, Any]], topn: int) -> List[str]:
    ranked = build_ranked_list(kpis)

    selected: List[str] = []
    selected_set = set()

    model_quota: Dict[str, int] = {}
    max_per_model = max(3, topn // 5)  # 防止单模型垄断
    max_time_compare = max(4, int(topn * 0.25))
    time_compare_count = 0

    # A) 每个 model 先保留一个 count
    for info in ranked:
        if info.kpi_id.endswith("_count") and info.comp_type == "aggregation":
            m = info.base_model or "unknown"
            if m not in model_quota:
                selected.append(info.kpi_id)
                selected_set.add(info.kpi_id)
                model_quota[m] = model_quota.get(m, 0) + 1
                if len(selected) >= topn:
                    return selected

    # B) 每个 model 再补一个高价值 monetary sum
    touched = set()
    for info in ranked:
        if "monetary" in info.tags and info.kpi_id.endswith("_sum"):
            m = info.base_model or "unknown"
            if m in touched:
                continue
            if model_quota.get(m, 0) >= max_per_model:
                continue
            if info.kpi_id not in selected_set:
                selected.append(info.kpi_id)
                selected_set.add(info.kpi_id)
                model_quota[m] = model_quota.get(m, 0) + 1
                touched.add(m)
                if len(selected) >= topn:
                    return selected

    # C) 优先补 formula
    for info in ranked:
        if info.comp_type != "formula":
            continue
        m = info.base_model or "unknown"
        if model_quota.get(m, 0) >= max_per_model:
            continue
        if info.kpi_id not in selected_set:
            selected.append(info.kpi_id)
            selected_set.add(info.kpi_id)
            model_quota[m] = model_quota.get(m, 0) + 1
            if len(selected) >= topn:
                return selected

    # D) 全局按分补齐（控制 time_compare 比例）
    for info in ranked:
        if info.kpi_id in selected_set:
            continue
        m = info.base_model or "unknown"
        if model_quota.get(m, 0) >= max_per_model:
            continue

        is_time_compare = info.comp_type == "period_compare" or info.kpi_id.endswith("_yoy") or info.kpi_id.endswith("_mom")
        if is_time_compare and time_compare_count >= max_time_compare:
            continue

        selected.append(info.kpi_id)
        selected_set.add(info.kpi_id)
        model_quota[m] = model_quota.get(m, 0) + 1
        if is_time_compare:
            time_compare_count += 1

        if len(selected) >= topn:
            break

    return selected


def collect_kpi_dependencies(kpi_id: str, kpis: Dict[str, Dict[str, Any]], visited: set | None = None) -> List[str]:
    """递归收集 KPI 依赖（formula dependencies + period_compare base_kpi）"""
    if visited is None:
        visited = set()
    if kpi_id in visited:
        return []
    visited.add(kpi_id)

    if kpi_id not in kpis:
        return []

    comp = (kpis[kpi_id].get("computation") or {})
    ctype = comp.get("type")

    deps: List[str] = []
    if ctype == "formula":
        for d in comp.get("dependencies", []) or []:
            if d in kpis:
                deps.append(d)
    elif ctype == "period_compare":
        bk = comp.get("base_kpi")
        if bk and bk in kpis:
            deps.append(bk)

    # 递归展开
    out: List[str] = []
    for d in deps:
        if d not in out:
            out.append(d)
        for dd in collect_kpi_dependencies(d, kpis, visited):
            if dd not in out:
                out.append(dd)
    return out


def write_report(report_path: Path, selected_ids: List[str], ranked: List[KPIInfo], kpis: Dict[str, Dict[str, Any]]):
    rank_map = {r.kpi_id: r for r in ranked}

    lines: List[str] = []
    lines.append("# KPI Curated Pack Report\n")
    lines.append(f"- Total KPIs: {len(kpis)}")
    lines.append(f"- Selected KPIs: {len(selected_ids)}\n")

    lines.append("## Selected KPI List\n")
    lines.append("| # | KPI ID | Name | Model | Type | Score |")
    lines.append("|---:|---|---|---|---|---:|")
    for i, kid in enumerate(selected_ids, 1):
        r = rank_map[kid]
        lines.append(f"| {i} | `{kid}` | {r.name} | `{r.base_model}` | `{r.comp_type}` | {r.score:.1f} |")

    lines.append("\n## Top 20 Ranked (Global)\n")
    lines.append("| # | KPI ID | Model | Type | Score |")
    lines.append("|---:|---|---|---|---:|")
    for i, r in enumerate(ranked[:20], 1):
        lines.append(f"| {i} | `{r.kpi_id}` | `{r.base_model}` | `{r.comp_type}` | {r.score:.1f} |")

    lines.append("\n## Scoring Notes\n")
    lines.append("- 偏好 aggregation / formula；period_compare 适度保留")
    lines.append("- monetary / rate / distinct_count 优先")
    lines.append("- 控制单模型占比和 YoY/MoM 比例，避免指标包失衡")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="从增强 KPI 集合筛选高价值 TopN KPI 包")
    parser.add_argument("input_osm", help="输入 OSM YAML")
    parser.add_argument("output_osm", help="输出 OSM YAML（只保留 TopN KPI）")
    parser.add_argument("--top", type=int, default=30, help="保留 KPI 数量，默认 30")
    parser.add_argument("--report", default="", help="输出报告路径（md）")
    args = parser.parse_args()

    in_path = Path(args.input_osm)
    out_path = Path(args.output_osm)
    report_path = Path(args.report) if args.report else out_path.with_suffix(".report.md")

    with in_path.open("r", encoding="utf-8") as f:
        osm = yaml.safe_load(f)

    kpis = osm.get("kpis", {}) or {}
    if not kpis:
        raise SystemExit("输入 OSM 中没有 kpis")

    selected_ids = select_top_kpis(kpis, args.top)

    # 补全依赖，保证 formula/period_compare 不悬挂
    selected_set = set(selected_ids)
    for kid in list(selected_ids):
        for dep in collect_kpi_dependencies(kid, kpis):
            if dep not in selected_set:
                selected_ids.append(dep)
                selected_set.add(dep)

    ranked = build_ranked_list(kpis)

    new_osm = copy.deepcopy(osm)
    new_osm["kpis"] = {kid: kpis[kid] for kid in selected_ids}

    # 同步 governance.role_permissions，避免 allowed_kpis 与实际 KPI 集漂移
    gov = new_osm.setdefault("governance", {})
    policies = gov.setdefault("policies", {})
    role_permissions = policies.get("role_permissions", {})
    if isinstance(role_permissions, dict):
        selected_set = set(selected_ids)
        for role, perm in role_permissions.items():
            if not isinstance(perm, dict):
                continue
            allowed = perm.get("allowed_kpis")
            if not isinstance(allowed, list):
                continue
            if "*" in allowed:
                continue
            # 仅保留仍存在的 KPI
            filtered = [k for k in allowed if k in selected_set]
            # 如果过滤后为空，降级给 curated 集，避免角色无可用 KPI
            perm["allowed_kpis"] = filtered if filtered else list(selected_ids)

    # 追加治理元数据（可选）
    gov = new_osm.setdefault("governance", {})
    policies = gov.setdefault("policies", {})
    policies["kpi_pack"] = {
        "name": f"curated_top_{args.top}",
        "source": str(in_path.name),
        "size": len(selected_ids),
    }

    with out_path.open("w", encoding="utf-8") as f:
        f.write("# ============================================================\n")
        f.write("# OSM (Ontology-Lite Semantic Model)\n")
        f.write("# Curated KPI Pack\n")
        f.write("# ============================================================\n\n")
        yaml.dump(new_osm, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)

    write_report(report_path, selected_ids, ranked, kpis)

    print("✅ Curated KPI pack generated")
    print(f"  - input kpis : {len(kpis)}")
    print(f"  - output kpis: {len(selected_ids)}")
    print(f"  - output yaml: {out_path}")
    print(f"  - report     : {report_path}")


if __name__ == "__main__":
    main()
