"""
测试 ddm-to-osm skill（P2）

覆盖：
1) 基础环境检查
2) 解析器单测（DDMParser）
3) 生成器单测（OSMGenerator basic/advanced + profile）
4) Golden 回归（sakila 关键计数与结构）
5) P1 结构断言（constraints/enums/filters/KPI 标准字段）
6) lint 与 curated 包一致性检查
7) P2 断言（model_version/source_fingerprint/report/diff/release manifest）
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

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

# 本地模块
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))


def ok(msg: str):
    print(f"   ✅ {msg}")


def warn(msg: str):
    print(f"   ⚠️  {msg}")


def fail(msg: str):
    print(f"   ❌ {msg}")


def find_sakila_ddm() -> Path | None:
    candidates = [
        ROOT / "examples" / "sample.ddm",
        ROOT.parent / "sakila_osm" / "sakila.ddm",
        ROOT.parent.parent / "sakila_osm" / "sakila.ddm",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_skill() -> int:
    print("🧪 测试 ddm-to-osm skill (P2)\n")
    all_passed = True

    # 1) Python 版本
    print("1️⃣ 检查 Python 版本...")
    if sys.version_info < (3, 8):
        fail(f"Python 版本过低: {sys.version}")
        fail("需要 Python 3.8 或更高版本")
        all_passed = False
    else:
        ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")

    # 2) 依赖
    print("\n2️⃣ 检查依赖...")
    try:
        import yaml  # noqa: F401
        ok("PyYAML 已安装")
    except Exception as e:
        fail(f"PyYAML 未安装或不可用: {e}")
        all_passed = False

    # 3) 文件结构
    print("\n3️⃣ 检查文件结构...")
    required_files = [
        "convert.py",
        "scripts/ddm_parser.py",
        "scripts/osm_generator.py",
        "curate_kpi_pack.py",
        "lint_osm.py",
        "diff_osm.py",
        "make_release_artifacts.py",
        "profile.example.yaml",
        "SKILL.md",
        "README.md",
        "skill.json",
        "LICENSE",
        "CHANGELOG.md",
        "requirements.txt",
    ]
    for file in required_files:
        if not (ROOT / file).exists():
            fail(f"缺少文件: {file}")
            all_passed = False
        else:
            ok(file)

    # 4) 导入
    print("\n4️⃣ 测试模块导入...")
    try:
        from ddm_parser import DDMParser
        from osm_generator import OSMGenerator
        from lint_osm import lint_osm
        ok("ddm_parser 导入成功")
        ok("osm_generator 导入成功")
        ok("lint_osm 导入成功")
    except Exception as e:
        fail(f"导入失败: {e}")
        return 1

    # 5) 解析器 + 生成器 + Golden + P1/P2 结构
    print("\n5️⃣ 解析器 / 生成器 / Golden / P1&P2 回归...")
    ddm_path = find_sakila_ddm()
    if not ddm_path:
        warn("未找到 sample.ddm / sakila.ddm，跳过解析与回归测试")
    else:
        try:
            import yaml
            from ddm_parser import DDMParser
            from lint_osm import lint_osm
            from osm_generator import OSMGenerator

            print(f"   使用 DDM: {ddm_path}")
            parser = DDMParser(str(ddm_path))
            entities = parser.parse()

            if len(entities) == 0:
                raise RuntimeError("解析结果为空")
            ok(f"解析实体数: {len(entities)}")

            # golden 关键值（仅在 sakila 上校验）
            is_sakila = ddm_path.name.lower() == "sakila.ddm"
            if is_sakila and len(entities) != 17:
                raise AssertionError(f"Golden 失败: 期望 17 entities, 实际 {len(entities)}")
            if is_sakila:
                ok("Golden: entity_count == 17")

            # 生成 basic/advanced/profile
            gen_basic = OSMGenerator(entities, database_name="sakila", kpi_mode="basic", source_name=str(ddm_path))
            osm_basic = gen_basic.generate()

            gen_adv = OSMGenerator(entities, database_name="sakila", kpi_mode="advanced", source_name=str(ddm_path))
            osm_adv = gen_adv.generate()

            profile_path = ROOT / "profile.example.yaml"
            profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
            gen_profiled = OSMGenerator(
                entities,
                database_name="sakila",
                kpi_mode="basic",
                source_name=str(ddm_path),
                profile=profile,
            )
            osm_profiled = gen_profiled.generate()

            # 基础结构断言
            for name, osm in [("basic", osm_basic), ("advanced", osm_adv), ("profiled", osm_profiled)]:
                if "meta" not in osm:
                    raise AssertionError(f"{name}: 缺少 meta")
                if "ontology" not in osm or "entities" not in osm["ontology"]:
                    raise AssertionError(f"{name}: ontology 结构不完整")
                if "semantic_models" not in osm:
                    raise AssertionError(f"{name}: 缺少 semantic_models")
                if "join_graph" not in osm:
                    raise AssertionError(f"{name}: 缺少 join_graph")
                if "kpis" not in osm:
                    raise AssertionError(f"{name}: 缺少 kpis")
            ok("basic/advanced/profiled 结构完整")

            # KPI 数量关系
            b_cnt = len(osm_basic.get("kpis", {}))
            a_cnt = len(osm_adv.get("kpis", {}))
            if a_cnt < b_cnt:
                raise AssertionError(f"KPI 数量异常: advanced({a_cnt}) < basic({b_cnt})")
            ok(f"KPI 数量: basic={b_cnt}, advanced={a_cnt}")

            # KPI time + P1 字段结构断言
            any_kpi = next(iter(osm_adv["kpis"].values())) if osm_adv["kpis"] else None
            if any_kpi:
                t = any_kpi.get("time", {})
                req_t = {"dimension", "default_grain", "allowed_grains", "window"}
                miss = req_t - set(t.keys())
                if miss:
                    raise AssertionError(f"KPI time 结构缺失字段: {sorted(miss)}")

                cons = any_kpi.get("constraints", {})
                deps = any_kpi.get("dependencies", {})
                for k in ["require_time", "require_host", "allowed_filters"]:
                    if k not in cons:
                        raise AssertionError(f"KPI constraints 缺少字段: {k}")
                for k in ["metrics", "entities"]:
                    if k not in deps:
                        raise AssertionError(f"KPI dependencies 缺少字段: {k}")
                ok("KPI 标准字段（time/constraints/dependencies）已对齐")

            # Ontology P1 字段
            sample_entity = next(iter(osm_adv["ontology"]["entities"].values()))
            if "constraints" not in sample_entity or "enums" not in sample_entity:
                raise AssertionError("Ontology 缺少 constraints/enums")
            ok("Ontology 包含 constraints/enums")

            # Semantic Model P1 字段
            sample_model = next(iter(osm_adv["semantic_models"].values()))
            if "filters" not in sample_model:
                raise AssertionError("Semantic model 缺少 filters")
            ok("Semantic model 包含 filters")

            # profile 覆写断言
            customer = osm_profiled["ontology"]["entities"].get("Customer", {})
            if "vip_level" not in (customer.get("enums") or {}):
                raise AssertionError("profile enums 覆写失败: Customer.vip_level 缺失")

            customer_filters = ((osm_profiled["semantic_models"].get("customer") or {}).get("filters") or {})
            if "region_scope" not in customer_filters:
                raise AssertionError("profile filters 覆写失败: customer.region_scope 缺失")

            payment_joins = ((osm_profiled["semantic_models"].get("payment") or {}).get("joins") or {})
            if "rental_payment_join" not in payment_joins:
                raise AssertionError("profile joins 覆写失败: rental_payment_join 缺失")
            cond = (payment_joins["rental_payment_join"].get("condition") or {})
            if cond.get("type") != "expression":
                raise AssertionError("profile joins 覆写失败: rental_payment_join 不是 expression")
            if any(k in cond for k in ["local_key", "foreign_key", "local_keys", "foreign_keys"]):
                raise AssertionError("expression join 仍残留 key join 字段")
            ok("profile 覆写（enums/filters/expression join）通过")

            # semantic_type / inverse 回归
            try:
                st = osm_basic["ontology"]["entities"]["Country"]["attributes"]["country"]["semantic_type"]
                if st == "count":
                    raise AssertionError("semantic_type 回归失败: Country.country 被误判为 count")
                ok(f"semantic_type 回归通过: Country.country={st}")
            except KeyError:
                warn("未找到 Country.country，跳过 semantic_type 回归断言")

            try:
                rels = osm_basic["ontology"]["entities"]["Address"].get("relations", [])
                if rels:
                    inv = rels[0].get("inverse")
                    if inv == "addresss":
                        raise AssertionError("inverse 命名回归失败: addresss")
                    ok(f"inverse 命名回归通过: {inv}")
            except KeyError:
                warn("未找到 Address 实体，跳过 inverse 回归断言")

            # lint 检查
            lint_basic = lint_osm(osm_basic)
            lint_adv = lint_osm(osm_adv)
            if lint_basic.errors:
                raise AssertionError(f"lint basic errors: {lint_basic.errors[:3]}")
            if lint_adv.errors:
                raise AssertionError(f"lint advanced errors: {lint_adv.errors[:3]}")
            ok("lint_osm 对 basic/advanced 通过")

            # 保存临时文件 + curate + lint + P2
            with tempfile.TemporaryDirectory() as td:
                td = Path(td)
                adv_path = td / "adv.yaml"
                top_path = td / "top.yaml"

                gen_adv.save_yaml(str(adv_path))
                if not adv_path.exists() or adv_path.stat().st_size == 0:
                    raise AssertionError("save_yaml 失败")

                # 调用 curate 脚本
                proc = run_cmd(
                    [
                        sys.executable,
                        str(ROOT / "curate_kpi_pack.py"),
                        str(adv_path),
                        str(top_path),
                        "--top",
                        "30",
                    ]
                )
                if proc.returncode != 0:
                    raise AssertionError(f"curate_kpi_pack 执行失败: {proc.stderr or proc.stdout}")
                if not top_path.exists():
                    raise AssertionError("curate 输出文件不存在")

                top_doc = yaml.safe_load(top_path.read_text(encoding="utf-8")) or {}
                lint_top = lint_osm(top_doc)
                if lint_top.errors:
                    raise AssertionError(f"curated lint errors: {lint_top.errors[:3]}")

                # governance allowed_kpis 一致性断言
                top_kpis = set((top_doc.get("kpis") or {}).keys())
                role_permissions = (((top_doc.get("governance") or {}).get("policies") or {}).get("role_permissions") or {})
                for role, perm in role_permissions.items():
                    if not isinstance(perm, dict):
                        continue
                    allowed = perm.get("allowed_kpis")
                    if isinstance(allowed, list) and "*" not in allowed:
                        missing = [x for x in allowed if x not in top_kpis]
                        if missing:
                            raise AssertionError(f"curated governance 漂移: role={role}, missing={missing[:5]}")
                ok("curate + lint + governance 一致性通过")

                # -------- P2 断言 --------
                p2_out = td / "p2.yaml"
                p2_report = td / "p2.report.md"

                proc = run_cmd(
                    [
                        sys.executable,
                        str(ROOT / "convert.py"),
                        str(ddm_path),
                        str(p2_out),
                        "sakila",
                        "--kpi-mode",
                        "advanced",
                        "--profile",
                        str(ROOT / "profile.example.yaml"),
                        "--report",
                        str(p2_report),
                    ]
                )
                if proc.returncode != 0:
                    raise AssertionError(f"convert.py(P2) 执行失败: {proc.stderr or proc.stdout}")
                if not p2_out.exists() or not p2_report.exists():
                    raise AssertionError("P2 convert 产物缺失（yaml/report）")

                p2_doc = yaml.safe_load(p2_out.read_text(encoding="utf-8")) or {}
                p2_meta = p2_doc.get("meta") or {}
                if not p2_meta.get("model_version"):
                    raise AssertionError("P2: meta.model_version 缺失")
                fp = str(p2_meta.get("source_fingerprint") or "")
                if not fp.startswith("sha256:"):
                    raise AssertionError("P2: meta.source_fingerprint 格式错误")
                ok("P2 meta 字段（model_version/source_fingerprint）通过")

                # diff_osm
                diff_md = td / "p2.diff.md"
                diff_json = td / "p2.diff.json"
                proc = run_cmd(
                    [
                        sys.executable,
                        str(ROOT / "diff_osm.py"),
                        str(adv_path),
                        str(p2_out),
                        "--md",
                        str(diff_md),
                        "--json",
                        str(diff_json),
                    ]
                )
                if proc.returncode != 0:
                    raise AssertionError(f"diff_osm.py 执行失败: {proc.stderr or proc.stdout}")
                if not diff_md.exists() or not diff_json.exists():
                    raise AssertionError("P2 diff 产物缺失")
                diff_doc = json.loads(diff_json.read_text(encoding="utf-8"))
                if "summary" not in diff_doc:
                    raise AssertionError("P2 diff.json 缺少 summary")
                ok("P2 diff_osm 报告生成通过")

                # make_release_artifacts
                release_dir = td / "release"
                proc = run_cmd(
                    [
                        sys.executable,
                        str(ROOT / "make_release_artifacts.py"),
                        str(ddm_path),
                        str(release_dir),
                        "sakila",
                        "--profile",
                        str(ROOT / "profile.example.yaml"),
                        "--kpi-mode",
                        "advanced",
                        "--top",
                        "30",
                        "--baseline",
                        str(adv_path),
                    ]
                )
                if proc.returncode != 0:
                    raise AssertionError(f"make_release_artifacts.py 执行失败: {proc.stderr or proc.stdout}")

                manifest_path = release_dir / "manifest.json"
                if not manifest_path.exists():
                    raise AssertionError("P2: manifest.json 缺失")
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

                # 核心字段断言
                for key in ["artifacts", "lint", "summary"]:
                    if key not in manifest:
                        raise AssertionError(f"P2 manifest 缺少字段: {key}")

                if manifest.get("lint", {}).get("osm", {}).get("errors", 1) != 0:
                    raise AssertionError("P2 manifest: osm lint errors 非 0")
                if manifest.get("lint", {}).get("curated", {}).get("errors", 1) != 0:
                    raise AssertionError("P2 manifest: curated lint errors 非 0")
                ok("P2 release manifest 校验通过")

            # 快照
            snap = {
                "entities": len(osm_adv["ontology"]["entities"]),
                "semantic_models": len(osm_adv["semantic_models"]),
                "join_edges": len(osm_adv["join_graph"]["edges"]),
                "kpis_basic": b_cnt,
                "kpis_advanced": a_cnt,
            }
            print("   Snapshot:", json.dumps(snap, ensure_ascii=False))

        except Exception as e:
            fail(f"解析/生成/回归测试失败: {e}")
            all_passed = False

    print("\n" + "=" * 56)
    if all_passed:
        print("✨ 所有测试通过！")
        print("\n使用方法:")
        print("  python convert.py <ddm_file> <output_yaml> [database_name] [--kpi-mode basic|advanced] [--profile profile.yaml] [--report report.md]")
        print("  python diff_osm.py <old_osm.yaml> <new_osm.yaml> --md diff.md --json diff.json")
        print("  python make_release_artifacts.py <ddm_file> <output_dir> [database_name] [--profile ...] [--baseline ...]")
        return 0

    print("❌ 部分测试失败")
    print("请查看上面的错误信息并修复，或查看 docs/TROUBLESHOOTING.md")
    return 1


if __name__ == "__main__":
    sys.exit(test_skill())
