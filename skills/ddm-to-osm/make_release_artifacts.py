#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_release_artifacts.py

P2 发布产物打包脚本：
1) 生成 OSM
2) 生成生成报告
3) lint 检查
4) 生成 curated KPI 包
5) 再次 lint
6) 可选与 baseline 做 diff
7) 输出 manifest.json

用法：
python make_release_artifacts.py <ddm_file> <output_dir> [database_name]
  [--profile profile.yaml]
  [--kpi-mode basic|advanced]
  [--top 30]
  [--baseline old_osm.yaml]
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any

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

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from convert import convert_ddm_to_osm, load_profile
from lint_osm import lint_osm


def yaml_load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_py(script: Path, args: list[str]):
    cmd = [sys.executable, str(script), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"{script.name} failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc.stdout


def main():
    parser = argparse.ArgumentParser(description="生成发布产物（OSM/report/curated/diff/manifest）")
    parser.add_argument("ddm_file", help="输入 DDM 文件")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("database_name", nargs="?", default="database", help="数据库名")
    parser.add_argument("--profile", default="", help="profile 配置路径")
    parser.add_argument("--kpi-mode", choices=["basic", "advanced"], default="advanced", help="KPI 模式")
    parser.add_argument("--top", type=int, default=30, help="curated topN")
    parser.add_argument("--baseline", default="", help="可选：baseline OSM 用于 diff")
    args = parser.parse_args()

    ddm = Path(args.ddm_file)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ddm.exists():
        print(f"❌ DDM 文件不存在: {ddm}")
        sys.exit(2)

    profile = {}
    if args.profile:
        profile = load_profile(args.profile)

    stem = ddm.stem
    osm_path = out_dir / f"{stem}.osm.yaml"
    report_path = out_dir / f"{stem}.report.md"
    curated_path = out_dir / f"{stem}.top{args.top}.yaml"
    curated_report_path = out_dir / f"{stem}.top{args.top}.report.md"

    diff_md = out_dir / f"{stem}.diff.md"
    diff_json = out_dir / f"{stem}.diff.json"

    print("[1/6] 生成 OSM...")
    convert_ddm_to_osm(
        ddm_file=str(ddm),
        output_file=str(osm_path),
        database_name=args.database_name,
        kpi_mode=args.kpi_mode,
        profile=profile,
        report=str(report_path),
    )

    print("[2/6] Lint OSM...")
    doc = yaml_load(osm_path)
    lint1 = lint_osm(doc, strict=False)
    if lint1.errors:
        print("❌ OSM lint failed:")
        for e in lint1.errors:
            print(" -", e)
        sys.exit(1)

    print("[3/6] 生成 curated KPI 包...")
    run_py(
        ROOT / "curate_kpi_pack.py",
        [str(osm_path), str(curated_path), "--top", str(args.top), "--report", str(curated_report_path)],
    )

    print("[4/6] Lint curated...")
    cdoc = yaml_load(curated_path)
    lint2 = lint_osm(cdoc, strict=False)
    if lint2.errors:
        print("❌ Curated lint failed:")
        for e in lint2.errors:
            print(" -", e)
        sys.exit(1)

    diff_generated = False
    if args.baseline:
        baseline = Path(args.baseline)
        if baseline.exists():
            print("[5/6] 生成 diff 报告...")
            run_py(
                ROOT / "diff_osm.py",
                [str(baseline), str(osm_path), "--md", str(diff_md), "--json", str(diff_json)],
            )
            diff_generated = True
        else:
            print(f"⚠️ baseline 不存在，跳过 diff: {baseline}")

    print("[6/6] 写入 manifest...")
    manifest = {
        "ddm": str(ddm),
        "database": args.database_name,
        "kpi_mode": args.kpi_mode,
        "profile": args.profile or None,
        "artifacts": {
            "osm": str(osm_path),
            "report": str(report_path),
            "curated_osm": str(curated_path),
            "curated_report": str(curated_report_path),
            "diff_md": str(diff_md) if diff_generated else None,
            "diff_json": str(diff_json) if diff_generated else None,
        },
        "lint": {
            "osm": {"errors": len(lint1.errors), "warnings": len(lint1.warnings)},
            "curated": {"errors": len(lint2.errors), "warnings": len(lint2.warnings)},
        },
        "summary": {
            "osm_kpis": len((doc.get("kpis") or {})),
            "curated_kpis": len((cdoc.get("kpis") or {})),
            "entities": len(((doc.get("ontology") or {}).get("entities") or {})),
        },
    }

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("✅ 发布产物已生成")
    print(f"- OSM: {osm_path}")
    print(f"- Report: {report_path}")
    print(f"- Curated: {curated_path}")
    print(f"- Curated Report: {curated_report_path}")
    if diff_generated:
        print(f"- Diff MD: {diff_md}")
        print(f"- Diff JSON: {diff_json}")
    print(f"- Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
