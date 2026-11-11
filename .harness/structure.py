#!/usr/bin/env python3
"""Connect native Python analyses to workflow evidence; no source parser here."""
import argparse
import ast
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import uuid
from collections import Counter
from contextlib import contextmanager

from common import (GateError, require, safe_path, strings, read_json, digest, file_sha, SKIP_DIRS,
                    project_entries, now, write_json, validate_checks, execute_check)
import quality_history

TOPICS = ("reuse", "semantic_duplication", "responsibilities", "dependencies", "simplicity", "impact")
TOOL_VERSIONS = {"jscpd": "5.4.0", "tach": "0.35.3"}


def validate_settings(root, settings):
    policy = settings.get("structural_quality")
    if policy is None:
        return
    require(isinstance(policy, dict), "structural_qualityはオブジェクトです")
    require(policy.get("mode") in ("observe", "enforce"), "構造検査のmodeはobserve/enforceです")
    for key in ("source_roots", "clone_roots"):
        for relative in strings(policy.get(key), f"structural_quality.{key}", 1):
            safe_path(root, relative)
            require(not relative.startswith((".harness", ".agents")), "配布基盤をアプリ解析rootにできません")
    for key in ("jscpd_config", "tach_config"):
        safe_path(root, policy.get(key))
    require(policy["tach_config"] == "tach.toml", "Tachはrootのtach.tomlを読みます")
    required = strings(policy.get("required_checks"), "structural_quality.required_checks", 1)
    require(len(set(required)) == len(required), "構造検査IDが重複しています")
    checks = {entry["id"]: entry for entry in settings["checks"]}
    for name in required:
        require(name in checks and checks[name]["argv"][1:] == [".harness/structure.py", "check"],
                "必須構造検査は .harness/structure.py check を実行します")
    scope_files(root, settings, policy["source_roots"])
    quality_history.load_policy(root, settings)


def validate_contract(root, phase, item, baseline_files=None):
    if phase == "discovery":
        candidates = item.get("reuse_candidates")
        require(isinstance(candidates, list), "reuse_candidatesの調査記録が必要です")
        for candidate in candidates:
            require(isinstance(candidate, dict), "再利用候補が不正です")
            path = safe_path(root, candidate.get("path"))
            require(path.is_file() or candidate["path"] in (baseline_files or {}),
                    "再利用候補のファイルが現在・開始時のどちらにもありません")
            strings([candidate.get("symbol"), candidate.get("decision")], "再利用候補の根拠", 2)
        if not candidates:
            strings([item.get("reuse_search")], "既存資産なしの検索根拠", 1)
    elif phase == "design":
        for relative in strings(item.get("affected_paths"), "design.affected_paths"):
            safe_path(root, relative)
        strings(item.get("new_module_reasons"), "design.new_module_reasons")
    elif phase == "review":
        review = item.get("structural_review")
        require(isinstance(review, dict) and set(review) == set(TOPICS), "構造レビューの全項目が必要です")
        strings(list(review.values()), "構造レビューの根拠", len(TOPICS))


def invoke(argv, root, allowed=(0,), timeout=60):
    result = subprocess.run(argv, cwd=root, text=True, capture_output=True, timeout=timeout)
    require(result.returncode in allowed, f"解析コマンド失敗: {argv[0]}: {result.stderr or result.stdout}")
    return result


def toolchain(root):
    observed = {}
    for name, expected in TOOL_VERSIONS.items():
        executable = shutil.which(name)
        require(executable is not None, f"解析ツールがありません: {name}")
        version = invoke([executable, "--version"], root).stdout.strip()
        require(version == f"{name} {expected}", f"固定した版が必要です: {name} {expected} (実際: {version})")
        observed[name] = {"version": expected, "path": executable, "sha256": file_sha(Path(executable))}
    try:
        native = importlib.metadata.distribution("tach")
    except importlib.metadata.PackageNotFoundError as exc:
        raise GateError("解析ツールと同じ検査用Pythonを使用してください") from exc
    observed["tach"]["engine_sha256"] = {
        str(path): file_sha(Path(native.locate_file(path))) for path in native.files
        if str(path).endswith((".so", ".pyd"))}
    observed["tach"]["networkx_version"] = importlib.metadata.version("networkx")
    return {"tools": observed, "python": platform.python_version(), "platform": platform.platform()}


def scanner_policy(root, settings):
    policy = settings["structural_quality"]
    clone_config = read_json(safe_path(root, policy["jscpd_config"]))
    require(set(clone_config) <= {"minTokens", "minLines", "mode"},
            "jscpdの除外・実験機能はこのPythonプロファイルで使用できません")
    require(type(clone_config.get("minTokens", 50)) is int and clone_config.get("minTokens", 50) > 0 and
            type(clone_config.get("minLines", 5)) is int and clone_config.get("minLines", 5) > 0,
            "重複検出の閾値が不正です")
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # Tach's Python 3.10 dependency; not needed by the workflow CLI.
    native = tomllib.loads(safe_path(root, policy["tach_config"]).read_text())
    require(native.get("source_roots", ["."]) == policy["source_roots"], "Tachと解析対象rootが一致しません")
    exclusions = native.get("exclude", [])
    require(all(p in (".harness", ".agents", ".harness/**", ".agents/**") for p in exclusions),
            "Python解析root内を除外できません。rootを明示してください")
    require(not native.get("ignore_type_checking_imports", True), "TYPE_CHECKING内の依存も解析してください")
    require(native.get("root_module") == "forbid", "未定義モジュールを無視しないroot_module=forbidが必要です")
    scan_options = {key: native.get(key) for key in
                    ("source_roots", "exclude", "respect_gitignore", "ignore_type_checking_imports")}
    identity = {"source_roots": policy["source_roots"], "clone_roots": policy["clone_roots"],
                "jscpd": clone_config, "tach_scan": scan_options, "tools": TOOL_VERSIONS}
    if policy.get("cumulative"):
        identity["cumulative_metrics"] = "jscpd-complexity-and-sarif-v1"
    return digest(identity)


def analysis_contract(root, settings):
    policy = settings["structural_quality"]
    return digest({"source_roots": policy["source_roots"], "clone_roots": policy["clone_roots"],
        "jscpd": read_json(safe_path(root, policy["jscpd_config"])),
        "tach": file_sha(safe_path(root, policy["tach_config"])), "tools": TOOL_VERSIONS,
        "metrics": "jscpd-complexity-and-sarif-v1", "connector": file_sha(Path(__file__)),
        "assessment": file_sha(Path(quality_history.__file__))})


def scope_files(root, settings, roots):
    roots = [safe_path(root, p) for p in roots]
    entries = project_entries(root, settings)
    files = set()
    for base in roots:
        if base.is_file():
            candidates = [base]
        else:
            candidates = []
            for directory, dirs, names in os.walk(base, followlinks=False):
                dirs[:] = [name for name in dirs if name not in SKIP_DIRS | {".harness", ".agents"}]
                candidates.extend(Path(directory) / name for name in names if name.endswith(".py"))
        for path in candidates:
            relative = path.relative_to(root).as_posix()
            if relative.endswith(".py") and not relative.startswith((".harness/", ".agents/")):
                require(relative in entries, f"Python解析対象を指紋から除外できません: {relative}")
                safe_path(root, relative)
                files.add(relative)
    return sorted(files)


def cycle_sets(graph, renames=None):
    import networkx as nx  # Already a dependency of Tach; reuse its graph implementation.
    renames = renames or {}
    normalized = nx.DiGraph()
    for source, targets in graph.items():
        normalized.add_node(renames.get(source, source))
        normalized.add_edges_from((renames.get(source, source), renames.get(target, target)) for target in targets)
    cycles = []
    for members in nx.strongly_connected_components(normalized):
        if len(members) > 1 or any(normalized.has_edge(node, node) for node in members):
            cycles.append({"members": sorted(members),
                           "edges": sorted([a, b] for a, b in normalized.edges if a in members and b in members)})
    return sorted(cycles, key=lambda entry: entry["members"])


def diagnostic_identity(value):
    if isinstance(value, dict):
        return {key: diagnostic_identity(item) for key, item in value.items()
                if key not in ("line_number", "original_line_number")}
    if isinstance(value, list):
        return [diagnostic_identity(item) for item in value]
    return value


def scan(root, settings, before=None, renames=None):
    root = root.resolve()
    provenance = toolchain(root)
    policy = settings["structural_quality"]
    cumulative = bool(policy.get("cumulative"))
    policy_digest = scanner_policy(root, settings)
    if before is not None:
        require(before.get("policy_digest") == policy_digest, "解析条件がbaselineから変わっています")
    files = scope_files(root, settings, policy["source_roots"])
    clones = scope_files(root, settings, policy["clone_roots"])
    inventory = {path: entry for path, entry in project_entries(root, settings).items()
                 if path.endswith(".py") and not path.startswith((".harness/", ".agents/")) and not entry.get("missing")}
    require(files or not inventory, "Pythonコードが解析対象外にあります。空の成功にはできません")
    if before is not None:
        outside = (set(inventory) | set(before["python_inventory"])) - set(files) - set(before["coverage"]["python_files"])
        require(not any(inventory.get(path) != before["python_inventory"].get(path) for path in outside),
                "変更したPythonコードが解析対象外です。scopeを見直してください")
    require(set(clones) <= set(files), "重複検査rootをPython解析rootに含めてください")
    nonempty = []
    for relative in files:
        tree = ast.parse(safe_path(root, relative).read_bytes(), filename=relative)
        if tree.body:
            nonempty.append(relative)
    mapped = invoke([provenance["tools"]["tach"]["path"], "map"], root)
    graph = json.loads(mapped.stdout)
    require(isinstance(graph, dict) and all(isinstance(k, str) and isinstance(v, list) and
            all(isinstance(t, str) for t in v) for k, v in graph.items()), "Tachの依存mapが不正です")
    # The CLI map omits nodes without outgoing imports. Parse each inventory entry with
    # the same native engine, then require every reported internal-import source in the map.
    from tach import extension
    native_config, _ = extension.parse_project_config(safe_path(root, policy["tach_config"]))
    roots = [safe_path(root, relative) for relative in policy["source_roots"]]
    native_imports = {relative: [item.module_path for item in extension.get_project_imports(
        root, roots, safe_path(root, relative), native_config)] for relative in files}
    missing = [relative for relative, imports in native_imports.items() if imports and relative not in graph]
    require(not missing, f"Tachの解析対象漏れ: {missing}")
    graph = {path: sorted(set(graph.get(path, [])) & set(files)) for path in files}
    boundaries = invoke([provenance["tools"]["tach"]["path"], "check"], root, allowed=(0, 1))
    diagnostics = json.loads(extension.serialize_diagnostics_json(extension.check(root, native_config, True, True), False))
    errors = [diagnostic_identity(item) for item in diagnostics if '"Error"' in json.dumps(item)]
    require(boundaries.returncode == 0 or bool(errors), "Tachの失敗を構造診断として解釈できません")
    new_boundaries = [item for item in errors if before is None or item not in before["boundary_violations"]]
    with tempfile.TemporaryDirectory(prefix="codexenvset-scan-") as directory:
        scratch = Path(directory)
        baseline_file = scratch / "clones.json"
        base_args = [provenance["tools"]["jscpd"]["path"], "--config", str(safe_path(root, policy["jscpd_config"])),
                     "--format", "python", "--no-colors"]
        args = [*base_args, "--reporters", "json,sarif" if cumulative else "json"]
        fingerprints, metrics = {}, {}
        if clones:
            # Probe coverage below the gate's thresholds; tiny modules must not disappear as an empty success.
            probe = scratch / "coverage"
            invoke([*args, "--min-tokens", "1", "--min-lines", "1", "--output", str(probe), *clones], root)
            counted = read_json(probe / "jscpd-report.json")["statistics"]["total"]["sources"]
            require(counted >= len(set(clones) & set(nonempty)), "jscpdの解析対象漏れを検出しました")
            if before is not None:
                baseline_file.write_text(json.dumps(before["clone_baseline"]))
                mode = ["--baseline", str(baseline_file)]
            else:
                mode = ["--baseline", str(baseline_file), "--update-baseline"]
            invoke([*args, "--output", str(scratch / "report"), *mode, *clones], root)
            duplication = read_json(scratch / "report/jscpd-report.json")
            clone_baseline = read_json(baseline_file)
            if cumulative:
                results = read_json(scratch / "report/jscpd-report.sarif")["runs"][0]["results"]
                fingerprints = dict(Counter(item["partialFingerprints"]["jscpdCloneHash/v1"] for item in results))
                require(sum(fingerprints.values()) == duplication["statistics"]["total"]["clones"],
                        "重複fingerprintの解析対象が一致しません")
        else:
            duplication = {"duplicates": [], "statistics": {"total": {"newClones": 0}}}
            clone_baseline = {"version": 1, "fingerprints": {}}
        if cumulative and files:
            invoke([*base_args, "--complexity", "--absolute", "--min-tokens", "1", "--min-lines", "1",
                    "--summary-top", str(len(files)), "--reporters", "json", "--output", str(scratch / "metrics"), *files], root)
            rows = read_json(scratch / "metrics/jscpd-complexity.json")["summary"]["files"]
            for row in rows:
                relative = Path(row["path"]).relative_to(root).as_posix()
                require(relative in files and relative not in metrics, "複雑性の解析対象が不正です")
                metrics[relative] = {key: row[key] for key in ("complexity", "tokens", "lines", "bytes")}
            require(set(nonempty) <= set(metrics), "複雑性の解析対象漏れを検出しました")
            for relative in set(files) - set(metrics):
                metrics[relative] = {"complexity": 0, "tokens": 0, "lines": 0,
                                     "bytes": safe_path(root, relative).stat().st_size}
    cycles = cycle_sets(graph)
    normalized = cycle_sets(graph, renames)
    old = before["cycles"] if before is not None else cycles
    new_cycles = [cycle for cycle in normalized if not any(
        set(cycle["members"]) <= set(previous["members"]) and
        set(map(tuple, cycle["edges"])) <= set(map(tuple, previous["edges"])) for previous in old)]
    report = {"schema_version": 1, "project_digest": digest(project_entries(root, settings)),
            "policy_digest": policy_digest, "provenance": provenance,
            "applicability": "python" if files else "empty", "coverage": {"python_files": files, "clone_files": clones},
            "python_inventory": inventory, "out_of_scope_python": sorted(set(inventory) - set(files)),
            "graph": graph, "native_imports": native_imports, "cycles": cycles, "new_cycles": new_cycles,
            "reidentified_cycles": [cycle for cycle in normalized if cycle in old and cycle not in cycles],
            "rename_candidates": renames or {}, "clone_baseline": clone_baseline,
            "duplication": duplication,
            "new_clones": duplication["statistics"]["total"].get("newClones", 0) if before is not None else 0,
            "boundaries_passed": boundaries.returncode == 0,
            "boundary_violations": errors, "new_boundary_violations": new_boundaries,
            "boundary_output": boundaries.stdout + boundaries.stderr}
    if cumulative:
        report.update(complexity=metrics, clone_fingerprints=fingerprints)
    return report


def cumulative_assessment(root, settings, report, base, config_path=".harness/project.json"):
    policy = quality_history.load_policy(root, settings)
    require(policy["analysis_digest"] == analysis_contract(root, settings), "承認した解析契約が変わっています")
    history = quality_history.collect_history(root, settings, policy, base, config_path)
    observations = {}
    executions = []
    for commit in history["sample_shas"]:
        with git_snapshot(root, commit, settings) as snapshot:
            native = scan(snapshot, {**settings, "verification_inputs": []})
        _, renames = quality_history.changed_paths(root, policy["adopted_sha"], commit)
        observations[commit] = quality_history.project(native, policy, renames)
        executions.append({"sha": commit, "project_digest": native["project_digest"],
                           "scanner_policy_digest": native["policy_digest"], "provenance": native["provenance"]})
    _, renames = quality_history.changed_paths(root, policy["adopted_sha"])
    current = quality_history.project(report, policy, renames)
    context = {}
    change = os.environ.get("HARNESS_CHANGE_ID")
    if change:
        path = safe_path(root, f".harness/changes/{change}/design.json")
        if path.is_file():
            design = read_json(path)
            context = {key: design[key] for key in ("root_causes", "responsibility_changes", "legacy_paths") if key in design}
    context["verification_digest"] = digest(settings.get("checks", []))
    inputs = project_entries(root, settings)
    context["verification_inputs_digest"] = digest({path: inputs[path] for path in settings.get("verification_inputs", [])})
    result = quality_history.assess(current, observations, history, policy,
        coupling=quality_history.change_coupling(history, policy), context=context)
    result.update(mode=settings["structural_quality"]["cumulative"]["mode"], analysis_digest=policy["analysis_digest"],
                  historical_execution=executions)
    return result


def standalone_review(root, settings, assessment, relative):
    path = safe_path(root, relative)
    review, review_digest = read_json(path), file_sha(path)
    require(assessment["status"] != "BLOCK", "重大な構造違反をレビューだけで解除できません")
    require(review.get("subject_digest") == assessment["subject_digest"], "累積レビューの対象が一致しません")
    validate_checks(settings.get("checks"))
    checks = [entry for entry in settings["checks"] if entry["id"] not in settings["structural_quality"].get("required_checks", [])]
    require(checks, "レビューには実行する挙動検証を登録してください")
    before = digest(project_entries(root, settings))
    token = uuid.uuid4().hex
    directory = safe_path(root, f".harness/changes/scan-{token}/evidence")
    directory.mkdir(parents=True)
    env = {key: value for key, value in os.environ.items() if not key.startswith("HARNESS_")}
    results = []
    for entry in checks:
        result = execute_check(root, directory, token, entry, env)
        results.append(result)
        if result["returncode"] != 0 or result["timed_out"]:
            break
    analysis = directory / "analysis.json"
    write_json(analysis, assessment)
    receipt = {"success": False, "project_digest": before, "checks": checks, "checks_digest": digest(checks), "results": results,
        "analysis": {"log": analysis.relative_to(root).as_posix(), "log_digest": file_sha(analysis)},
        "source_unchanged": before == digest(project_entries(root, settings)),
        "review_digest": review_digest, "subject_digest": assessment["subject_digest"]}
    write_json(directory / "receipt.json", receipt)
    require(receipt["source_unchanged"] and file_sha(path) == review_digest, "挙動検証中に対象が変更されています")
    require(len(results) == len(checks) and all(entry["returncode"] == 0 and not entry["timed_out"] for entry in results),
            f"累積レビューの挙動検証が失敗しました: {directory.relative_to(root)}")
    quality_history.validate_review(root, assessment, review, {entry["id"] for entry in results})
    receipt.update(success=True, cumulative_review=review, design=assessment["context"])
    write_json(directory / "receipt.json", receipt)
    return receipt


def git_renames(root, base):
    if not base:
        return {}
    output = invoke(["git", "diff", "--name-status", "-z", "--find-renames", base, "--"], root).stdout.split("\0")
    renames = {}
    index = 0
    while index < len(output) and output[index]:
        status = output[index]
        index += 1
        if status.startswith(("R", "C")):
            old, new = output[index:index + 2]
            index += 2
            if status.startswith("R"):
                renames[new] = old
        else:
            index += 1
    require(len(set(renames.values())) == len(renames), "改名対応が曖昧です")
    return renames


@contextmanager
def git_snapshot(root, base, settings):
    resolved = invoke(["git", "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}"], root).stdout.strip()
    archive = subprocess.run(["git", "archive", "--format=tar", resolved], cwd=root, capture_output=True, timeout=60)
    require(archive.returncode == 0, "Git基準の内容を取得できません")
    with tempfile.TemporaryDirectory(prefix="codexenvset-base-") as directory:
        snapshot = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as stream:
            for member in stream:
                target = safe_path(snapshot, member.name.rstrip("/"))
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    require(member.isfile(), "Git基準のリンク・特殊ファイルは解析できません")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(stream.extractfile(member).read())
        # Compare source trees using one declared scanner policy, never head-selected baseline data.
        for key in ("jscpd_config", "tach_config"):
            relative = settings["structural_quality"][key]
            target = safe_path(snapshot, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(safe_path(root, relative).read_bytes())
        yield snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description="Python構造検査: native jscpd/Tachの基準比較")
    parser.add_argument("command", choices=("baseline", "check", "scan", "policy"))
    parser.add_argument("--project", type=Path, default=Path(os.environ.get("HARNESS_PROJECT", ".")))
    parser.add_argument("--config", default=".harness/project.json")
    parser.add_argument("--base", help="配布元等の単独検査で比較するGitコミット")
    parser.add_argument("--review", help="単独scanの独立した累積レビューJSON。登録済みの挙動検証も実行します")
    parser.add_argument("--project-id", help="policy候補を作る対象の安定した識別子")
    args = parser.parse_args(argv)
    root = args.project.resolve()
    try:
        settings = read_json(safe_path(root, args.config))
        if args.command == "policy":
            require(args.base and args.project_id, "policyには--baseと--project-idが必要です")
            anchor = invoke(["git", "rev-parse", "--verify", "--end-of-options", f"{args.base}^{{commit}}"], root).stdout.strip()
            roots = settings["structural_quality"]["source_roots"]
            candidate = {"schema_version": 1, "project_id": args.project_id, "epoch": "initial",
                "adopted_sha": anchor, "anchor_sha": anchor, "analysis_digest": analysis_contract(root, settings),
                "window_changes": 20, "window_days": 90, "review_changes": 20, "review_days": 90,
                "thresholds": quality_history.DEFAULTS,
                "responsibilities": [{"id": f"responsibility-{index + 1}", "paths": [path.rstrip("/") + "/**" if path != "." else "**"],
                                      "purpose": ""} for index, path in enumerate(roots)]}
            print(json.dumps(candidate, ensure_ascii=False, indent=2))
            return 0
        before_identity = digest(project_entries(root, settings))
        base = os.environ.get("HARNESS_CI_BASE") or args.base
        before = None
        if args.command != "baseline":
            if base:
                with git_snapshot(root, base, settings) as snapshot:
                    # Added verification inputs belong to the current execution, not the old source tree.
                    before = scan(snapshot, {**settings, "verification_inputs": []})
            elif args.command == "check":
                before = read_json(Path(os.environ["HARNESS_BASELINE_LOG"]))
        rename_base = base
        change = os.environ.get("HARNESS_CHANGE_ID")
        if not rename_base and change:
            state = read_json(safe_path(root, f".harness/changes/{change}/state.json"))
            rename_base = state.get("base_sha")
        renames = git_renames(root, rename_base)
        if before is not None:
            renames = {new: old for new, old in renames.items() if old in before["graph"] and
                       not (root / old).exists() and (root / new).is_file()}
        report = scan(root, settings, before, renames=renames)
        if settings["structural_quality"].get("cumulative"):
            history_base = rename_base or invoke(["git", "rev-parse", "HEAD"], root).stdout.strip()
            report["cumulative"] = cumulative_assessment(root, settings, report, history_base, args.config)
        require(report["project_digest"] == before_identity == digest(project_entries(root, settings)),
                "構造解析中に対象が変更されています")
        violations = report["new_clones"] > 0 or bool(report["new_cycles"]) or bool(report["new_boundary_violations"])
        report.update(ok=args.command == "baseline" or settings["structural_quality"]["mode"] == "observe" or not violations,
                      ci_base_sha=base, started_identity=before_identity, finished_at=now())
        cumulative = report.get("cumulative")
        reviewed = False
        if args.review:
            require(args.command == "scan" and cumulative, "--reviewは累積品質の単独scanで使用します")
            report["verification"] = standalone_review(root, settings, cumulative, args.review)
            reviewed = True
        if cumulative and args.command != "baseline" and cumulative["mode"] == "enforce":
            report["ok"] = report["ok"] and cumulative["status"] != "BLOCK" and (
                args.command == "check" or cumulative["status"] == "PASS" or reviewed)
        if cumulative:
            report.update(quality_status="PASS" if reviewed else cumulative["status"],
                          quality_enforced=cumulative["mode"] == "enforce")
        print(json.dumps(report, ensure_ascii=False))
        return 0 if report["ok"] else 1
    except (GateError, OSError, ValueError, KeyError, TypeError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"ok": False, "execution_status": "invalid", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
