"""
convert.py - DDM 到 OSM 转换主脚本

使用方法:
    python convert.py <ddm_file> <output_yaml> [database_name] [--kpi-mode basic|advanced] [--profile profile.yaml]

示例:
    python convert.py sakila.ddm sakila_osm.yaml sakila --kpi-mode basic
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
from pathlib import Path
from typing import Dict, Any

import yaml

# 修复 Windows 控制台编码问题（避免重复包装导致流关闭）
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

# 添加 scripts 目录到 path（使用 Path 处理跨平台路径）
script_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(script_dir))

from ddm_parser import DDMParser
from osm_generator import OSMGenerator


def load_profile(profile_path: str) -> Dict[str, Any]:
    if not profile_path:
        return {}
    p = Path(profile_path)
    if not p.exists():
        raise FileNotFoundError(f"Profile 文件不存在: {profile_path}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Profile 文件必须是 YAML 对象")
    return data


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_summary(osm: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "entities": len(((osm.get("ontology") or {}).get("entities") or {})),
        "semantic_models": len(osm.get("semantic_models") or {}),
        "join_edges": len(((osm.get("join_graph") or {}).get("edges") or [])),
        "kpis": len(osm.get("kpis") or {}),
    }


def write_report_md(report_path: str, ddm_file: str, output_file: str, summary: Dict[str, Any], extra: Dict[str, Any]):
    lines = [
        "# DDM to OSM Generation Report",
        "",
        f"- Input DDM: `{ddm_file}`",
        f"- Output OSM: `{output_file}`",
        "",
        "## Summary",
        "",
        f"- entities: {summary['entities']}",
        f"- semantic_models: {summary['semantic_models']}",
        f"- join_edges: {summary['join_edges']}",
        f"- kpis: {summary['kpis']}",
        "",
        "## Meta",
        "",
    ]
    for k, v in extra.items():
        lines.append(f"- {k}: `{v}`")

    Path(report_path).write_text("\n".join(lines), encoding="utf-8")


def convert_ddm_to_osm(
    ddm_file: str,
    output_file: str,
    database_name: str = "database",
    kpi_mode: str = "advanced",
    profile: Dict[str, Any] | None = None,
    report: str = "",
):
    """
    将 DDM 文件转换为 OSM YAML

    Args:
        ddm_file: DDM 文件路径
        output_file: 输出的 OSM YAML 文件路径
        database_name: 数据库名称
        kpi_mode: KPI 生成模式 basic|advanced
        profile: 生成配置（可选）
        report: markdown 报告路径（可选）
    """
    # -------- phase 1: 输入检查 --------
    if not os.path.exists(ddm_file):
        print(f"❌ 输入错误: DDM 文件不存在: {ddm_file}")
        print("\n请检查:")
        print("  1. 文件路径是否正确")
        print("  2. 文件是否存在")
        print("  3. 是否有读取权限")
        sys.exit(1)

    print(f"📖 解析 DDM 文件: {ddm_file}")

    # -------- phase 2: 解析 --------
    try:
        parser = DDMParser(ddm_file)
        entities = parser.parse()
    except Exception as e:
        print(f"❌ 解析失败 (ParseError): {e}")
        print("\n请检查:")
        print("  1. DDM 文件格式是否正确（应为 XML 格式）")
        print("  2. 文件是否是 Datablau LDM 格式")
        print("  3. 文件编码是否为 UTF-8")
        print("\n查看 docs/TROUBLESHOOTING.md 获取更多帮助")
        sys.exit(1)

    print(f"✅ 解析到 {len(entities)} 个实体")
    print("\n实体列表:")
    for entity_name, entity in entities.items():
        print(f"  - {entity_name} ({entity.label}): {len(entity.attributes)} 个属性, {len(entity.foreign_keys)} 个外键")

    # -------- phase 3: 生成 --------
    print("\n🔨 生成 OSM 模型...")
    try:
        generator = OSMGenerator(
            entities,
            database_name,
            kpi_mode=kpi_mode,
            profile=profile or {},
            source_name=ddm_file,
        )
        osm = generator.generate()
    except Exception as e:
        print(f"❌ 生成失败 (GenerateError): {e}")
        print("\n查看 docs/TROUBLESHOOTING.md 获取帮助")
        sys.exit(1)

    # P2: 注入版本与来源指纹
    ddm_hash = file_sha256(ddm_file)
    meta = osm.setdefault("meta", {})
    meta["model_version"] = profile.get("model_version") if isinstance(profile, dict) else None
    if not meta.get("model_version"):
        meta["model_version"] = "v1"
    meta["source_fingerprint"] = f"sha256:{ddm_hash}"

    summary = make_summary(osm)

    print("✅ 生成完成:")
    print(f"  - Ontology 实体: {summary['entities']}")
    print(f"  - Semantic Models: {summary['semantic_models']}")
    print(f"  - Join Graph 边: {summary['join_edges']}")
    print(f"  - KPIs: {summary['kpis']}")
    print(f"  - KPI 模式: {kpi_mode}")

    # -------- phase 4: 输出 --------
    print(f"\n💾 保存到: {output_file}")
    try:
        generator.osm = osm
        generator.save_yaml(output_file)
    except Exception as e:
        print(f"❌ 保存失败 (OutputError): {e}")
        print("\n请检查:")
        print("  1. 是否有写入权限")
        print("  2. 磁盘空间是否充足")
        print("  3. 文件是否被其他程序占用")
        sys.exit(1)

    # 可选报告
    if report:
        extra = {
            "kpi_mode": kpi_mode,
            "model_version": meta.get("model_version"),
            "source_fingerprint": meta.get("source_fingerprint"),
            "database": database_name,
        }
        write_report_md(report, ddm_file, output_file, summary, extra)
        print(f"📄 报告已生成: {report}")

    print("\n✨ 转换完成！")
    print("\n下一步:")
    print(f"  1. 检查生成的 {output_file} 文件")
    print("  2. 运行 lint: python lint_osm.py <output_yaml>")
    print("  3. 如需 KPI 精选包，运行 curate_kpi_pack.py")


def main():
    parser = argparse.ArgumentParser(description="DDM 到 OSM 转换工具")
    parser.add_argument("ddm_file", help="DDM 文件路径 (.ddm)")
    parser.add_argument("output_yaml", help="输出的 OSM YAML 文件路径")
    parser.add_argument("database_name", nargs="?", default="database", help="数据库名称 (可选，默认为 'database')")
    parser.add_argument("--kpi-mode", choices=["basic", "advanced"], default="advanced", help="KPI 生成模式")
    parser.add_argument("--profile", default="", help="YAML 配置文件路径（可选）")
    parser.add_argument("--report", default="", help="生成 Markdown 报告路径（可选）")

    args = parser.parse_args()

    try:
        profile = load_profile(args.profile) if args.profile else {}
    except Exception as e:
        print(f"❌ Profile 加载失败 (InputError): {e}")
        sys.exit(1)

    convert_ddm_to_osm(
        ddm_file=args.ddm_file,
        output_file=args.output_yaml,
        database_name=args.database_name,
        kpi_mode=args.kpi_mode,
        profile=profile,
        report=args.report,
    )


if __name__ == "__main__":
    main()
