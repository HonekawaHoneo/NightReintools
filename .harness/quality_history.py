"""Bind cumulative quality to Git evidence; reuse native analysis, never parse source."""
import fnmatch
import json
import re
import subprocess

from common import GateError, SKIP_DIRS, digest, nonempty, project_entries, read_json, require, safe_path, sha, strings, validate_checks

SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
DEFAULTS = {"repeat_changes": 4, "branch_growth": 5, "branch_ratio": 0.20,
            "anchor_growth": 10, "anchor_ratio": 0.25, "fanout_growth": 2,
            "coupling_shared": 5, "coupling_ratio": 0.60, "coupling_increase": 0.15}


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=60)
    require(result.returncode == 0, "累積品質のGit履歴・固定基準を取得できません")
    return result.stdout.decode("utf-8", errors="surrogateescape")


def in_scope(path, roots):
    return (path.endswith(".py") and not set(path.split("/")) & (SKIP_DIRS | {".harness", ".agents"}) and
            any(root == "." or path == root or path.startswith(root.rstrip("/") + "/") for root in roots))


def responsibility(policy, path):
    matches = [entry["id"] for entry in policy["responsibilities"]
               if any(fnmatch.fnmatchcase(path, pattern) for pattern in entry["paths"])]
    require(len(matches) == 1, f"構造品質の責務が未定義・重複です: {path}")
    return matches[0]


def load_policy(root, settings):
    profile = settings.get("structural_quality", {}).get("cumulative")
    if profile is None:
        return None
    require(isinstance(profile, dict) and set(profile) == {"mode", "policy"} and
            profile["mode"] in ("observe", "enforce"), "cumulativeのmode/policyが不正です")
    path = safe_path(root, profile["policy"])
    relative = path.relative_to(root).as_posix()
    require(relative in project_entries(root, settings), "累積品質の方針を指紋から除外できません")
    policy = read_json(path)
    require(policy.get("schema_version") == 1, "累積品質のschema_versionが不正です")
    allowed = {"schema_version", "project_id", "epoch", "adopted_sha", "anchor_sha", "analysis_digest",
               "responsibilities", "thresholds", "window_changes", "window_days", "review_changes",
               "review_days", "previous"}
    require(set(policy) <= allowed, "累積品質の未知の設定があります")
    for key in ("project_id", "epoch"):
        nonempty(policy.get(key), f"quality.{key}")
    for key in ("adopted_sha", "anchor_sha"):
        require(isinstance(policy.get(key), str) and SHA.fullmatch(policy[key]), f"品質基準の固定SHAが必要です: {key}")
    require(isinstance(policy.get("analysis_digest"), str) and
            re.fullmatch(r"[0-9a-f]{64}", policy["analysis_digest"]), "解析契約の指紋が必要です")
    roles = policy.get("responsibilities")
    require(isinstance(roles, list) and roles, "責務の定義が必要です")
    ids = set()
    for entry in roles:
        require(isinstance(entry, dict), "責務の定義が不正です")
        name = nonempty(entry.get("id"), "responsibility.id")
        require(name not in ids, "責務IDが重複しています")
        ids.add(name)
        nonempty(entry.get("purpose"), "responsibility.purpose")
        for pattern in strings(entry.get("paths"), "responsibility.paths", 1):
            safe_path(root, pattern)
    for key, default in (("window_changes", 20), ("window_days", 90), ("review_changes", 20), ("review_days", 90)):
        value = policy.get(key, default)
        require(type(value) is int and 1 <= value <= 10000, f"{key}は1以上10000以下です")
    thresholds = policy.get("thresholds", {})
    require(isinstance(thresholds, dict) and set(thresholds) <= set(DEFAULTS), "累積閾値が不正です")
    for key, value in thresholds.items():
        require(type(value) in (int, float) and 0 < value <= 10000 and
                (not key.endswith(("ratio", "increase")) or value <= 1), f"累積閾値が不正です: {key}")
    for relative in project_entries(root, settings):
        if in_scope(relative, settings["structural_quality"]["source_roots"]):
            responsibility(policy, relative)
    return policy


def changed_paths(root, before, after=None):
    args = ["diff", "--name-status", "-z", "--find-renames", before]
    if after:
        args.append(after)
    records = git(root, *args, "--").split("\0")
    paths, renames, index = set(), {}, 0
    while index < len(records) and records[index]:
        status, path = records[index:index + 2]
        index += 2
        paths.add(path)
        if status.startswith(("R", "C")):
            target = records[index]
            index += 1
            paths.add(target)
            if status.startswith("R"):
                renames[target] = path
    return sorted(paths), renames


def committed_metadata(root, base):
    files = {}
    for record in git(root, "ls-tree", "-r", "-z", base, "--", ".harness/changes").split("\0"):
        if record:
            meta, path = record.split("\t", 1)
            mode, kind, blob = meta.split()
            if mode in ("100644", "100755") and kind == "blob":
                files[path] = blob
    result = []
    cache = {}
    def contents(path):
        require(path in files, "完了履歴の実行証跡がありません")
        if path not in cache:
            cache[path] = git(root, "cat-file", "blob", files[path])
        return cache[path]
    def proof(receipt, review, required=()):
        """Validate fixed execution links, without rerunning historical checks."""
        inputs = []
        def log(reference):
            path = reference["log"]
            safe_path(root, path)
            value = contents(path)
            require(sha(value.encode("utf-8", errors="surrogateescape")) == reference["log_digest"], "履歴ログが不一致です")
            inputs.append((path, value))
            return value
        try:
            require(receipt.get("success") is True and receipt.get("source_unchanged") is True, "履歴の検証が未完了です")
            checks, results = receipt["checks"], receipt["results"]
            validate_checks(checks)
            require(checks and digest(checks) == receipt["checks_digest"] and len(checks) == len(results), "履歴の全検証が必要です")
            reports = []
            for check, entry in zip(checks, results):
                require(entry["id"] == check["id"] and entry["argv"] == check["argv"] and
                        entry["returncode"] == 0 and entry["timed_out"] is False, "履歴の実行結果が不正です")
                value = log(entry)
                if entry["id"] in required:
                    report = json.loads(value)
                    require(report.get("ok") is True and report.get("project_digest") == receipt["project_digest"], "履歴の解析対象が不一致です")
                    reports.append(report["cumulative"])
            require(set(required) <= {entry["id"] for entry in results}, "履歴の構造検査が不足しています")
            if required:
                require(all(receipt.get(key) and receipt[key] == review.get(key)
                            for key in ("project_digest", "artifacts_digest")), "履歴のレビューが古いです")
                cumulative = review["cumulative_review"]
            else:
                reports.append(json.loads(log(receipt["analysis"])))
                cumulative = review
                require(receipt["subject_digest"] == cumulative["subject_digest"], "履歴のレビュー対象が不一致です")
            require(reports and set(cumulative.get("behavior_checks", [])) <=
                    {entry["id"] for entry in results} - set(required), "履歴の挙動検証が不足しています")
            for analysis in reports:
                require(analysis["execution_status"] == "complete" and analysis["status"] in ("PASS", "REVIEW_REQUIRED") and
                        all(analysis[key] == cumulative[key] for key in ("subject_digest", "policy_digest")) and
                        set(cumulative["scope"]) >= set(analysis["scope"]) and
                        all(cumulative["group_digests"].get(role) == value for role, value in analysis["group_digests"].items()),
                        "履歴の解析とレビューが不一致です")
            return inputs
        except (GateError, ValueError, KeyError, TypeError, AttributeError):
            return []
    def append_record(directory, names, data, design, review, verified=False):
        integrated = git(root, "log", "-1", "--first-parent", "--format=%H", base, "--", *names).strip()
        result.append({"id": directory.rsplit("/", 1)[1], "commit": base, "design": design, "review": review,
                       "integrated_sha": integrated, "checkpoint_verified": verified,
                       "integrated_time": int(git(root, "show", "-s", "--format=%ct", integrated)),
                       "inputs": [{"path": name, "blob": files[name], "digest":
                                   sha(value.encode("utf-8", errors="surrogateescape")) if isinstance(value, str) else digest(value)}
                                  for name, value in zip(names, data)]})
    for path in sorted(files):
        if re.fullmatch(r"\.harness/changes/[^/]+/evidence/receipt\.json", path):
            receipt = json.loads(contents(path))
            require(isinstance(receipt, dict), "単独検査の履歴証跡が不正です")
            review = receipt.get("cumulative_review", {})
            verified = proof(receipt, review)
            if verified:
                append_record(path.rsplit("/", 2)[0], [path] + [name for name, _ in verified],
                              [receipt] + [value for _, value in verified], receipt.get("design", {}),
                              {"decision": "passed", "cumulative_review": review}, True)
            continue
        if not re.fullmatch(r"\.harness/changes/[^/]+/state\.json", path):
            continue
        directory = path.rsplit("/", 1)[0]
        names = [f"{directory}/{name}.json" for name in ("state", "design", "review")]
        if not all(name in files for name in names):
            continue
        data = [json.loads(contents(name)) for name in names]
        require(all(isinstance(value, dict) for value in data), "履歴メタデータが不正です")
        if data[0].get("phase") == "done" and data[2].get("decision") == "passed":
            verified = []
            required = (data[0].get("structural_quality") or {}).get("required_checks", [])
            if required:
                for candidate in sorted(files):
                    if re.fullmatch(re.escape(directory) + r"/evidence/[0-9a-f]{32}\.json", candidate):
                        receipt = json.loads(contents(candidate))
                        links = proof(receipt, data[2], required)
                        if links:
                            verified = [(candidate, receipt), *links]
                            break
            append_record(directory, names + [name for name, _ in verified], data + [value for _, value in verified],
                          data[1], data[2], bool(verified))
    return result


def collect_history(root, settings, policy, base_sha, config_path=".harness/project.json"):
    require(git(root, "rev-parse", "--is-shallow-repository").strip() == "false", "shallowな履歴では累積品質を確認できません")
    require(isinstance(base_sha, str) and SHA.fullmatch(base_sha), "累積比較の固定base SHAが必要です")
    base = git(root, "rev-parse", "--verify", "--end-of-options", f"{base_sha}^{{commit}}").strip()
    policy_path = settings["structural_quality"]["cumulative"]["policy"]
    # Follow the base configuration, including an approved policy-file move.
    prior_path = policy_path
    config_entry = git(root, "ls-tree", base, "--", config_path).strip()
    prior_profile = None
    if config_entry:
        original_settings = json.loads(git(root, "cat-file", "blob", config_entry.split()[2]))
        prior_profile = (original_settings.get("structural_quality") or {}).get("cumulative")
        if prior_profile:
            prior_path = prior_profile["policy"]
    safe_path(root, prior_path)
    prior_entry = git(root, "ls-tree", base, "--", prior_path).strip()
    require(not prior_profile or prior_entry, "既存の品質方針が履歴にありません")
    prior_blob = prior_entry.split()[2] if prior_entry else None
    changed_epoch = False
    if prior_blob:
        original = json.loads(git(root, "cat-file", "blob", prior_blob))
        require(original.get("project_id") == policy["project_id"] and original.get("adopted_sha") == policy["adopted_sha"],
                "既存の導入履歴を新しい基準で消すことはできません")
        changed_epoch = any(original.get(key) != policy.get(key) for key in ("anchor_sha", "epoch", "analysis_digest", "responsibilities"))
        require(not changed_epoch or policy.get("previous"), "基準更新には旧品質基準の固定参照が必要です")
    head = git(root, "rev-parse", "HEAD").strip()
    for old, new in ((policy["adopted_sha"], policy["anchor_sha"]), (policy["anchor_sha"], base), (base, head)):
        git(root, "merge-base", "--is-ancestor", old, new)
    chain = git(root, "rev-list", "--first-parent", base).splitlines()
    require(policy["anchor_sha"] in chain and policy["adopted_sha"] in chain,
            "品質基準が取り込み履歴の祖先にありません")
    roots = settings["structural_quality"]["source_roots"]
    transactions = []
    for commit in reversed(chain[:chain.index(policy["adopted_sha"])]):
        parent = git(root, "rev-parse", f"{commit}^1").strip()
        paths, renames = changed_paths(root, parent, commit)
        paths = [path for path in paths if in_scope(path, roots)]
        if paths:
            transactions.append({"sha": commit, "parent": parent,
                "tree": git(root, "rev-parse", f"{commit}^{{tree}}").strip(),
                "timestamp": int(git(root, "show", "-s", "--format=%ct", commit)),
                "paths": paths, "renames": {new: old for new, old in renames.items() if new in paths},
                "responsibilities": sorted({responsibility(policy, path) for path in paths})})
    count = policy.get("window_changes", 20)
    reference_time = int(git(root, "show", "-s", "--format=%ct", base))
    cutoff = reference_time - policy.get("window_days", 90) * 86400
    recent = transactions[-count:]
    period = [item for item in transactions if item["timestamp"] >= cutoff]
    samples = {policy["adopted_sha"], policy["anchor_sha"], base}
    samples.update(window[0]["parent"] for window in (recent, period) if window)
    changed, _ = changed_paths(root, base)
    changed += git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    scope = sorted({responsibility(policy, path) for path in changed if in_scope(path, roots)})
    manifest = {"schema_version": 1, "project_id": policy["project_id"], "epoch": policy["epoch"],
        "base_sha": base, "anchor_sha": policy["anchor_sha"], "adopted_sha": policy["adopted_sha"],
        "policy_path": policy_path, "base_policy_path": prior_path,
        "policy_digest": digest(policy), "reference_time": reference_time,
        "adopted_time": int(git(root, "show", "-s", "--format=%ct", policy["adopted_sha"])),
        "transactions": transactions,
        "commit_order": list(reversed(chain[:chain.index(policy["adopted_sha"]) + 1])),
        "windows": {"changes": [item["sha"] for item in recent], "period": [item["sha"] for item in period]},
        "window_bases": {name: window[0]["parent"] if window else base
                         for name, window in (("changes", recent), ("period", period))},
        "sample_shas": sorted(samples), "changed_responsibilities": scope,
        "scope": scope or sorted(entry["id"] for entry in policy["responsibilities"]),
        "metadata": committed_metadata(root, base), "sampling": "anchor-and-window-endpoints"}
    previous = policy.get("previous")
    if previous:
        require(isinstance(previous, dict) and set(previous) == {"commit", "path"} and
                SHA.fullmatch(previous["commit"]), "旧品質基準の固定参照が必要です")
        safe_path(root, previous["path"])
        # Initial target adoption may bring a versioned policy from the merged branch.
        # Once the base owns a policy, its fixed lineage remains mandatory.
        git(root, "merge-base", "--is-ancestor", previous["commit"], base if prior_blob else head)
        blob = git(root, "rev-parse", f"{previous['commit']}:{previous['path']}").strip()
        require(not changed_epoch or blob == prior_blob, "基準更新の旧品質基準が実際のbaseと一致しません")
        prior = json.loads(git(root, "cat-file", "blob", blob))
        require(prior["project_id"] == policy["project_id"] and prior["adopted_sha"] == policy["adopted_sha"] and
                prior["epoch"] != policy["epoch"], "基準更新で導入履歴を変更できません")
        manifest["previous"] = {**previous, "blob": blob, "policy": prior}
    manifest["history_digest"] = digest(manifest)
    return manifest


def project(report, policy, renames=None):
    """Project native file metrics/debt onto the declared responsibilities."""
    files = report["coverage"]["python_files"]
    metrics = report.get("complexity")
    require(isinstance(metrics, dict) and set(metrics) == set(files), "複雑性の解析対象が一致しません")
    groups = {entry["id"]: {"files": [], "decisions": 0, "max_complexity": 0,
                           "tokens": 0, "lines": 0, "dependencies": []} for entry in policy["responsibilities"]}
    owners = {path: responsibility(policy, path) for path in files}
    for path in files:
        metric, group = metrics[path], groups[owners[path]]
        require(all(type(metric.get(key)) is int and metric[key] >= 0
                    for key in ("complexity", "tokens", "lines", "bytes")), "native複雑性の値が不正です")
        group["files"].append(path)
        group["decisions"] += max(0, metric["complexity"] - 1)
        group["max_complexity"] = max(group["max_complexity"], metric["complexity"])
        group["tokens"] += metric["tokens"]
        group["lines"] += metric["lines"]
        group["dependencies"].extend(owners[target] for target in report["graph"].get(path, [])
                                     if target in owners and owners[target] != owners[path])
    for group in groups.values():
        group["files"].sort()
        group["dependencies"] = sorted(set(group["dependencies"]))
    renames = renames or {}
    debts = {}
    fingerprints = report.get("clone_fingerprints")
    require(isinstance(fingerprints, dict), "native重複fingerprintの観測がありません")
    for fingerprint, units in fingerprints.items():
        require(isinstance(fingerprint, str) and type(units) is int and units > 0, "native重複fingerprintが不正です")
        debts["clone:" + fingerprint] = {"kind": "clone", "units": units}
    for cycle in report["cycles"]:
        for source, target in cycle["edges"]:
            edge = [renames.get(source, source), renames.get(target, target)]
            debts["cycle:" + digest(edge)] = {"kind": "cycle", "units": 1, "edge": edge}
    for diagnostic in report["boundary_violations"]:
        # The native connector already removes line positions from diagnostic identity.
        debts["boundary:" + digest(diagnostic)] = {"kind": "boundary", "units": 1, "diagnostic": diagnostic}
    return {"source_digest": digest({path: report["python_inventory"][path] for path in files}),
            "groups": groups, "debts": debts}


def change_coupling(manifest, policy):
    """Reuse NetworkX's native overlap projection; no custom coupling engine."""
    import networkx as nx
    from networkx.algorithms import bipartite
    transactions = manifest["transactions"]
    count = policy.get("window_changes", 20)
    cutoff = manifest["reference_time"] - policy.get("window_days", 90) * 86400
    windows = {"changes": (transactions[-count:], transactions[-2 * count:-count]),
        "period": ([item for item in transactions if item["timestamp"] >= cutoff],
                   [item for item in transactions if cutoff - policy.get("window_days", 90) * 86400 <= item["timestamp"] < cutoff])}
    def project_window(items):
        graph = nx.Graph()
        for item in items:
            graph.add_edges_from((("role", role), ("commit", item["sha"])) for role in item["responsibilities"])
        roles = sorted(node for node in graph if node[0] == "role")
        if not roles:
            return {}
        weights = bipartite.overlap_weighted_projected_graph(graph, roles)
        counts = bipartite.weighted_projected_graph(graph, roles)
        return {(source[1], target[1]): {"source": source[1], "target": target[1],
                 "ratio": weight["weight"], "shared": counts[source][target]["weight"]}
                for source, target, weight in weights.edges(data=True)}
    result = {}
    for name, (current, previous) in windows.items():
        old = project_window(previous)
        result[name] = [{**entry, "previous_ratio": old.get(pair, {}).get("ratio", 0)}
                        for pair, entry in sorted(project_window(current).items())]
    return result


def assess(current, observations, manifest, policy, *, coupling, context=None):
    require(set(manifest["sample_shas"]) <= set(observations), "必要な履歴観測がありません")
    require(isinstance(coupling, dict), "変更結合の解析が未実行です")
    findings, thresholds = [], {**DEFAULTS, **policy.get("thresholds", {})}
    order = manifest.get("commit_order", [entry["sha"] for entry in manifest["transactions"]])
    positions = {commit: index for index, commit in enumerate(order)}
    checkpoints = [entry for entry in manifest["metadata"]
                   if entry.get("checkpoint_verified") is True and entry.get("integrated_sha") in positions and
                   entry["review"].get("cumulative_review", {}).get("policy_digest") == digest(policy)]
    revalidated = set()
    scope = set(manifest["scope"])
    for role in list(scope):
        scope.update(current["groups"][role]["dependencies"])
        scope.update(other for other, group in current["groups"].items() if role in group["dependencies"])
    def finding(rule, subject, severity, evidence, confidence="signal", identifier=None):
        item = {"rule": rule, "subject": subject, "severity": severity,
                "confidence": confidence, "evidence": evidence}
        findings.append({"id": identifier or digest(item), **item})
    def grew(new, old, absolute, ratio):
        return new - old >= absolute and (old == 0 or (new - old) / old >= ratio)
    anchor = observations[manifest["anchor_sha"]]
    adopted = observations[manifest["adopted_sha"]]
    for role in sorted(scope):
        group = current["groups"][role]
        matching = [entry for entry in checkpoints if
                    entry["review"]["cumulative_review"].get("group_digests", {}).get(role) == digest(group)]
        if matching:
            revalidated.add(max(matching, key=lambda entry: positions[entry["integrated_sha"]])["id"])
            continue
        for name, revisions in manifest["windows"].items():
            relevant = [entry for entry in manifest["transactions"]
                        if entry["sha"] in revisions and role in entry["responsibilities"]]
            old = observations[manifest["window_bases"][name]]["groups"][role]
            new_dependencies = sorted(set(group["dependencies"]) - set(old["dependencies"]))
            if len(relevant) >= thresholds["repeat_changes"] and (
                grew(group["decisions"], old["decisions"], thresholds["branch_growth"], thresholds["branch_ratio"]) or
                len(new_dependencies) >= thresholds["fanout_growth"]):
                finding("cumulative_growth", role, "review", {"window": name, "changes": len(relevant),
                    "before": old["decisions"], "after": group["decisions"], "new_dependencies": new_dependencies})
        old = anchor["groups"][role]
        if grew(group["decisions"], old["decisions"], thresholds["anchor_growth"], thresholds["anchor_ratio"]):
            finding("anchor_drift", role, "review", {"anchor": manifest["anchor_sha"],
                    "before": old["decisions"], "after": group["decisions"]})
    for name, entries in coupling.items():
        for entry in entries:
            if {entry["source"], entry["target"]} & scope and entry["shared"] >= thresholds["coupling_shared"] and (
                entry["ratio"] >= thresholds["coupling_ratio"] and
                entry["ratio"] - entry["previous_ratio"] >= thresholds["coupling_increase"]):
                scope.update((entry["source"], entry["target"]))
                finding("change_coupling", f"{entry['source']}:{entry['target']}", "review", {"window": name, **entry})
    debt = {"retained": [], "resolved_observed": [], "new": [], "sampling": manifest.get("sampling", "endpoints")}
    for identifier, item in current["debts"].items():
        old = adopted["debts"].get(identifier, {}).get("units", 0)
        observed_floor = min(value["debts"].get(identifier, {}).get("units", 0) for value in observations.values())
        if item["units"] > old or (old and item["units"] > observed_floor):
            rule = "reopened_debt" if old and item["units"] > observed_floor else "new_structural_debt"
            debt["new"].append({"id": identifier, **item})
            finding(rule, identifier, "major", {"adopted_units": old, "observed_floor": observed_floor,
                    "current_units": item["units"]}, "native-confirmed")
        else:
            debt["retained"].append({"id": identifier, "first_seen_sha": manifest["adopted_sha"], **item})
    debt["resolved_observed"] = [{"id": identifier, **item} for identifier, item in adopted["debts"].items()
                                if identifier not in current["debts"]]
    context = context or {}
    for cause in context.get("root_causes", []):
        related = [entry["id"] for entry in manifest["metadata"]
                   if any(old.get("id") == cause["id"] for old in entry["design"].get("root_causes", []))]
        if cause.get("workaround") and len(related) >= 2:
            finding("workaround_chain", cause["id"], "review", {"prior_changes": related, "current": cause})
    whole = [entry for entry in checkpoints if entry["review"]["cumulative_review"].get("whole_design_review") is True and
             set(entry["review"]["cumulative_review"].get("scope", [])) >= set(current["groups"])]
    checkpoint = max(whole, key=lambda entry: positions[entry["integrated_sha"]]) if whole else None
    since = checkpoint["integrated_sha"] if checkpoint else manifest["adopted_sha"]
    since_time = checkpoint["integrated_time"] if checkpoint else manifest["adopted_time"]
    count = sum(positions[entry["sha"]] > positions.get(since, -1) for entry in manifest["transactions"])
    if (count >= policy.get("review_changes", 20) or
            manifest["reference_time"] - since_time >= policy.get("review_days", 90) * 86400):
        scope = set(current["groups"])
        finding("whole_design_review", policy["project_id"], "review", {"changes": count, "since": since})
    pending, aliases = {}, {}
    for entry in sorted(checkpoints, key=lambda value: positions[value["integrated_sha"]]):
        for disposition in entry["review"]["cumulative_review"].get("dispositions", []):
            obligation = aliases.get(disposition["id"], disposition["id"])
            identifier = digest({"rule": "deferred_signal_due", "obligation": obligation})
            aliases[identifier] = obligation
            if disposition.get("decision") == "deferred":
                pending[obligation] = (entry, disposition, identifier)
            else:
                pending.pop(obligation, None)
    for obligation, (entry, disposition, identifier) in pending.items():
        elapsed = sum(positions[item["sha"]] > positions[entry["integrated_sha"]] for item in manifest["transactions"])
        if set(entry["review"]["cumulative_review"].get("scope", [])) & scope and elapsed >= disposition["review_after_changes"]:
            finding("deferred_signal_due", obligation, "review", {"checkpoint": entry["id"], "changes": elapsed,
                    "obligation_id": obligation}, identifier=identifier)
    if "previous" in manifest and not checkpoint:
        scope = set(current["groups"])
        finding("epoch_bridge", policy["epoch"], "review", {"previous": manifest["previous"]["blob"],
                "measurement": "same-current-contract-not-original-observation"})
    status = "BLOCK" if any(item["severity"] == "major" for item in findings) else "REVIEW_REQUIRED" if findings else "PASS"
    subject = {"current": current, "observations": observations, "history_digest": manifest["history_digest"],
               "policy_digest": digest(policy), "coupling": coupling, "context": context}
    return {"schema_version": 1, "execution_status": "complete", "status": status,
            "subject_digest": digest(subject), "policy_digest": digest(policy), "history_digest": manifest["history_digest"],
            "scope": sorted(scope), "findings": findings, "debt": debt, "current": current,
            "group_digests": {role: digest(current["groups"][role]) for role in sorted(scope)},
            "revalidated_checkpoints": sorted(revalidated), "context": context,
            "observations": observations, "history": manifest, "coupling": coupling,
            "measurement": "normalized-under-pinned-analysis-contract", "evidence_kind": "static-analysis-and-git"}


def validate_assessment(root, settings, assessment, base):
    policy = load_policy(root, settings)
    require(isinstance(assessment, dict) and assessment.get("execution_status") == "complete" and
            assessment.get("mode") == settings["structural_quality"]["cumulative"]["mode"], "累積検査が未実施・不正です")
    history = collect_history(root, settings, policy, base)
    require(assessment.get("history") == history and assessment.get("analysis_digest") == policy["analysis_digest"],
            "累積検査の履歴・解析契約が実行時から変わっています")
    expected = assess(assessment["current"], assessment["observations"], history, policy,
                      coupling=assessment["coupling"], context=assessment["context"])
    for key in ("subject_digest", "status", "scope", "findings", "policy_digest", "history_digest", "group_digests"):
        require(assessment.get(key) == expected[key], f"累積検査の結果が一致しません: {key}")
    require(assessment["mode"] == "observe" or assessment["status"] != "BLOCK", "重大な累積構造違反が残っています")


def validate_design(root, policy, design, requirement_ids, check_ids):
    roles = {entry["id"] for entry in policy["responsibilities"]}
    changes = design.get("responsibility_changes")
    require(isinstance(changes, list), "設計にresponsibility_changesが必要です")
    declared = set()
    for entry in changes:
        require(isinstance(entry, dict) and entry.get("id") in roles and entry["id"] not in declared, "変更責務が不正です")
        declared.add(entry["id"])
        require(set(strings(entry.get("requirements"), "責務の要件", 1)) <= requirement_ids, "責務の要件参照が不正です")
        nonempty(entry.get("reason"), "責務の変更理由")
    causes = design.get("root_causes")
    require(isinstance(causes, list), "設計にroot_causesが必要です")
    ids = set()
    for cause in causes:
        name = nonempty(cause.get("id"), "root_cause.id")
        require(name not in ids and type(cause.get("workaround")) is bool, "根因ID・回避処理の分類が不正です")
        ids.add(name)
        nonempty(cause.get("reason"), "根因の根拠")
        require(set(strings(cause.get("checks"), "根因の検証", 1)) <= check_ids, "根因の検証が未登録です")
        for path in strings(cause.get("paths"), "根因のコード", 1):
            safe_path(root, path)
        if cause["workaround"]:
            nonempty(cause.get("removal_condition"), "回避処理の終了条件")
    for path in strings(design.get("legacy_paths"), "旧実装・互換処理"):
        safe_path(root, path)


def validate_review(root, assessment, review, completed_checks):
    require(assessment.get("execution_status") == "complete", "累積検査が完了していません")
    require(assessment.get("status") in ("PASS", "REVIEW_REQUIRED"), "BLOCK・重大違反を説明だけで解除できません")
    require(isinstance(review, dict) and review.get("subject_digest") == assessment["subject_digest"] and
            review.get("policy_digest") == assessment["policy_digest"], "累積レビューの対象が一致しません")
    scope = set(strings(review.get("scope"), "累積レビューのscope"))
    require(scope >= set(assessment["scope"]) and scope <= set(assessment["current"]["groups"]), "累積レビューの範囲が不足しています")
    require(review.get("group_digests") == {role: digest(assessment["current"]["groups"][role]) for role in scope},
            "累積レビューの構造状態が一致しません")
    whole = any(item["rule"] in ("whole_design_review", "epoch_bridge") for item in assessment["findings"])
    require(not whole or review.get("whole_design_review") is True, "全体設計の再評価が必要です")
    dispositions = review.get("dispositions")
    require(isinstance(dispositions, list) and len(dispositions) == len(assessment["findings"]) and
            {item.get("id") for item in dispositions} == {item["id"] for item in assessment["findings"]}, "累積所見の判断が不足しています")
    if assessment["findings"]:
        alternatives = review.get("alternatives")
        require(isinstance(alternatives, dict), "局所修正・構造整理・設計変更の比較が必要です")
        for key in ("local_fix", "scoped_refactor", "design_change"):
            nonempty(alternatives.get(key), key)
        checks = set(strings(review.get("behavior_checks"), "挙動の検証", 1))
        require(checks <= completed_checks, "累積レビューの挙動検証が実行されていません")
    for item in dispositions:
        require(item.get("decision") in ("explained", "resolved", "deferred"), "累積所見の判断が不正です")
        nonempty(item.get("reason"), "累積所見の根拠")
        evidence = item.get("evidence")
        require(isinstance(evidence, list) and evidence, "累積所見のコード根拠が必要です")
        scope_files = {path for role in scope for path in assessment["current"]["groups"][role]["files"]}
        require(any(entry.get("path") in scope_files for entry in evidence), "累積所見の対象コードの根拠が必要です")
        for entry in evidence:
            require(safe_path(root, entry.get("path")).is_file(), "累積レビューのコード根拠がありません")
            nonempty(entry.get("reason"), "コードの確認根拠")
        if item["decision"] == "deferred":
            nonempty(item.get("owner"), "延期の担当者")
            nonempty(item.get("removal_condition"), "延期の終了条件")
            require(type(item.get("review_after_changes")) is int and 1 <= item["review_after_changes"] <= 20,
                    "延期後の再確認期限が必要です")
    paths = assessment.get("context", {}).get("legacy_paths", [])
    cleanup = review.get("legacy_dispositions", [])
    require(isinstance(cleanup, list) and {item["path"] for item in cleanup} == set(paths), "旧実装の残存確認が不足しています")
    for item in cleanup:
        path = safe_path(root, item["path"])
        nonempty(item.get("reason"), "旧実装の判断根拠")
        require((item.get("decision") == "removed" and not path.exists()) or
                (item.get("decision") == "retained" and path.is_file() and item.get("removal_condition")),
                "旧実装の除去・互換処理の終了条件を確認してください")
    return "PASS"
