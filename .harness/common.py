"""Shared file identity and safe artifact I/O; Python standard library only."""
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import signal
from pathlib import Path
import subprocess
import tempfile

class GateError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def nonempty(value, label):
    require(isinstance(value, str) and value.strip() and
            value.strip().upper() not in {"TODO", "TBD", "未記入", "要記入"}, f"{label}: 内容が必要です")
    return value


def sequence(value, label, minimum=0):
    require(isinstance(value, list) and len(value) >= minimum, f"{label}: 配列（最低{minimum}件）が必要です")
    return value


def strings(value, label, minimum=0):
    items = sequence(value, label, minimum)
    for item in items:
        nonempty(item, label)
    return items


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def read_json(path):
    require(path.is_file(), f"成果物がありません: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateError(f"JSONを読めません: {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path}: JSONオブジェクトが必要です")
    return value


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temp = Path(stream.name)
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(temp, path)


def safe_path(root, relative):
    nonempty(relative, "path")
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in relative,
            f"プロジェクト内の相対パスが必要です: {relative}")
    target = root / path
    require(target.resolve().is_relative_to(root.resolve()), f"プロジェクト外への参照: {relative}")
    return target


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def project_entries(root, settings):
    try:
        probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root,
                               capture_output=True, text=True, check=False)
    except FileNotFoundError:
        probe = None
    if probe and probe.returncode == 0 and Path(probe.stdout.strip()).resolve() == root.resolve():
        result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                cwd=root, capture_output=True, check=False)
        require(result.returncode == 0, "Gitファイル一覧を取得できません")
        paths = {os.fsdecode(p) for p in result.stdout.split(b"\0") if p}
    else:
        paths = set()
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
            for name in list(dirs):
                path = Path(directory) / name
                if path.is_symlink():
                    paths.add(path.relative_to(root).as_posix())
                    dirs.remove(name)
            for name in files:
                paths.add((Path(directory) / name).relative_to(root).as_posix())
    extra = strings(settings.get("verification_inputs", []), "verification_inputs")
    for relative in extra:
        path = safe_path(root, relative)
        require(path.is_file(), f"検証入力がありません: {relative}")
        require(relative != ".harness/runtime.lock" and not relative.startswith(".harness/changes/") and
                not any(part in SKIP_DIRS for part in Path(relative).parts) and
                not any(fnmatch.fnmatchcase(relative, pattern) for pattern in settings.get("snapshot_ignore", [])),
                f"検証入力を除外できません: {relative}")
    paths.update(extra)
    entries = {}
    for relative in sorted(paths):
        parts = Path(relative).parts
        if (any(p in SKIP_DIRS for p in parts) or relative.startswith(".harness/changes/") or
                relative == ".harness/runtime.lock" or
                any(fnmatch.fnmatchcase(relative, p) for p in settings.get("snapshot_ignore", []))):
            continue
        path = safe_path(root, relative)
        if path.is_symlink():
            require(path.exists(), f"壊れたリンク: {relative}")
            target = path.resolve()
            require(target.is_file(), f"指紋対象のディレクトリリンクは使えません: {relative}")
            entries[relative] = {"link": os.readlink(path), "sha256": file_sha(target)}
        elif path.is_file():
            entries[relative] = {"sha256": file_sha(path), "executable": bool(path.stat().st_mode & 0o111)}
        else:
            entries[relative] = {"missing": True}
    return entries


def validate_checks(checks):
    ids = set()
    for entry in sequence(checks, "checks"):
        require(isinstance(entry, dict), "checksの各要素はオブジェクトです")
        name = nonempty(entry.get("id"), "check.id")
        require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", name) and name not in ids, f"不正・重複したcheck.id: {name}")
        ids.add(name)
        strings(entry.get("argv"), f"{name}.argv", 1)
        timeout = entry.get("timeout_seconds")
        require(type(timeout) in (int, float) and 0 < timeout <= 3600, f"{name}: timeout_secondsは0超3600以下です")


def execute_check(root, directory, token, entry, env):
    log = directory / f"{token}-{entry['id']}.log"
    started, timed_out = now(), False
    with log.open("wb") as output:
        try:
            process = subprocess.Popen(entry["argv"], cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=env)
            try:
                code = process.wait(timeout=entry["timeout_seconds"])
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
        except OSError as exc:
            output.write(str(exc).encode())
            code = 127
    return {"id": entry["id"], "argv": entry["argv"], "returncode": code,
            "timed_out": timed_out, "started_at": started, "finished_at": now(),
            "log": log.relative_to(root).as_posix(), "log_digest": file_sha(log)}
