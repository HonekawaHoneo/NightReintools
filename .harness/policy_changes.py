#!/usr/bin/env python3
"""Identify policy weakening for a protected CI approval job; never approve it."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import re
import subprocess
import tokenize


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise ValueError("Gitの固定基準を取得できません")
    return result.stdout


def project_weakened(old, new):
    old_checks = {entry["id"]: entry["argv"] for entry in old.get("checks", [])}
    new_checks = {entry["id"]: entry["argv"] for entry in new.get("checks", [])}
    if any(new_checks.get(name) != command for name, command in old_checks.items()):
        return True
    if not set(new.get("snapshot_ignore", [])) <= set(old.get("snapshot_ignore", [])):
        return True
    if not set(old.get("verification_inputs", [])) <= set(new.get("verification_inputs", [])):
        return True
    before, after = old.get("structural_quality"), new.get("structural_quality")
    if before:
        if not after or (before["mode"] == "enforce" and after.get("mode") != "enforce"):
            return True
        for key in ("source_roots", "clone_roots", "required_checks"):
            if not set(before[key]) <= set(after.get(key, [])):
                return True
        for key in ("jscpd_config", "tach_config"):
            if before.get(key) != after.get(key):
                return True
        old_cumulative, new_cumulative = before.get("cumulative"), after.get("cumulative")
        if old_cumulative != new_cumulative:
            if not old_cumulative or not new_cumulative or old_cumulative.get("policy") != new_cumulative.get("policy"):
                return True
            if old_cumulative.get("mode") == "enforce" and new_cumulative.get("mode") != "enforce":
                return True
    return False


def cumulative_weakened(old, new):
    # Only an explicitly lowered threshold is unambiguously a strengthening.
    if {key: value for key, value in old.items() if key != "thresholds"} != {
            key: value for key, value in new.items() if key != "thresholds"}:
        return True
    before, after = old.get("thresholds", {}), new.get("thresholds", {})
    if set(before) != set(after):
        return True
    return any(type(after[key]) not in (int, float) or type(value) not in (int, float) or
               not 0 < after[key] <= value for key, value in before.items())


def tach_weakened(old, new):
    for key in ("source_roots", "forbid_circular_dependencies", "exact", "root_module",
                "layers", "layers_explicit_depends_on", "interfaces", "rules"):
        if old.get(key) != new.get(key):
            return True  # Ambiguous architecture-policy changes require its owner, not an AI waiver.
    if not set(new.get("exclude", [])) <= set(old.get("exclude", [])):
        return True
    if not old.get("ignore_type_checking_imports", True) and new.get("ignore_type_checking_imports", True):
        return True
    def modules(config):
        result = {}
        for entry in config.get("modules", []):
            for path in entry.get("paths", [entry.get("path")]):
                result[path] = entry
        return result
    after = modules(new)
    for path, before in modules(old).items():
        if path not in after:
            return True
        entry = after[path]
        allowed = before.get("depends_on")
        if allowed is not None and (entry.get("depends_on") is None or not set(entry["depends_on"]) <= set(allowed)):
            return True
        if not set(before.get("cannot_depend_on", [])) <= set(entry.get("cannot_depend_on", [])):
            return True
        if entry.get("unchecked", False) and not before.get("unchecked", False):
            return True
        if any(before.get(key) != entry.get(key) for key in ("layer", "visibility", "strict", "utility")):
            return True
    return False


def tach_suppressions(source):
    """Bind native comments to logical statements, ignoring line moves and indentation."""
    groups, statement = [], []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NEWLINE:
            groups.append(tuple(statement))
            statement = []
        elif token.type == tokenize.COMMENT:
            if re.match(r"#\s*tach-ignore\b", token.string):
                statement.append((token.type, token.string))
        elif token.type not in (tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
            statement.append((token.type, token.string))
    groups.append(tuple(statement))
    return Counter(group for group in groups if any(kind == tokenize.COMMENT for kind, _ in group))


def weakening_changes(root, base):
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}").strip()
    tracked = git(root, "ls-tree", "-r", "--name-only", "-z", base).split("\0")
    changed = git(root, "diff", "--name-only", "-z", base, "--").split("\0")
    clone_configs = {".jscpd.json"}
    cumulative_configs = {"quality-policy.json", ".harness/quality-policy.json"}
    for relative in (".harness/project.json", "quality.json"):
        if relative in tracked:
            policy = json.loads(git(root, "show", f"{base}:{relative}")).get("structural_quality") or {}
            if policy.get("jscpd_config"):
                clone_configs.add(Path(policy["jscpd_config"]).as_posix())
            if policy.get("cumulative"):
                cumulative_configs.add(Path(policy["cumulative"]["policy"]).as_posix())
        if (root / relative).is_file():
            policy = json.loads((root / relative).read_text()).get("structural_quality") or {}
            if policy.get("cumulative"):
                cumulative_configs.add(Path(policy["cumulative"]["policy"]).as_posix())
    findings = []
    for relative in changed:
        if not relative:
            continue
        path = root / relative
        if relative in cumulative_configs:
            if relative not in tracked or not path.is_file() or cumulative_weakened(
                    json.loads(git(root, "show", f"{base}:{relative}")), json.loads(path.read_text())):
                findings.append(relative)
            continue
        if relative.endswith(".py"):
            before = git(root, "show", f"{base}:{relative}") if relative in tracked else ""
            after = path.read_text() if path.is_file() else ""
            if tach_suppressions(after) - tach_suppressions(before):
                findings.append(relative)
                continue
        if relative not in tracked:
            continue
        critical = (relative.startswith(("runtime/", ".github/workflows/")) or
                    relative in (".github/CODEOWNERS", "scripts/policy_changes.py", "requirements-quality.txt", "requirements-quality.in") or
                    (relative.startswith(".harness/") and not relative.startswith(".harness/changes/") and
                     relative != ".harness/project.json"))
        if critical:
            findings.append(relative)
            continue
        if relative not in clone_configs | {".harness/project.json", "quality.json", "tach.toml"}:
            continue
        if not path.is_file():
            findings.append(relative)
            continue
        before = git(root, "show", f"{base}:{relative}")
        if relative != "tach.toml":
            old, new = json.loads(before), json.loads(path.read_text())
            if relative.endswith("project.json") or relative == "quality.json":
                weakened = project_weakened(old, new)
            else:
                weakened = (new.get("minTokens", 50) > old.get("minTokens", 50) or
                            new.get("minLines", 5) > old.get("minLines", 5) or
                            new.get("mode", "mild") != old.get("mode", "mild") or
                            any(new.get(key) != value for key, value in old.items()
                                if key not in ("minTokens", "minLines", "mode")) or
                            bool(set(new) - set(old) - {"minTokens", "minLines", "mode"}))
        else:
            import tomllib  # CI policy inspection uses Python 3.12, independently of the workflow runtime.
            weakened = tach_weakened(tomllib.loads(before), tomllib.loads(path.read_text()))
        if weakened:
            findings.append(relative)
    return sorted(findings)


def main():
    parser = argparse.ArgumentParser(description="品質基準の弱化・ゲート変更を列挙する（承認は行わない）")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    print(json.dumps(weakening_changes(args.project.resolve(), args.base)))


if __name__ == "__main__":
    main()
