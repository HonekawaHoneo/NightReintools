#!/usr/bin/env python3
"""UI CLI and compatibility facade; validation lives in ui_rules."""
import argparse
import json
from pathlib import Path
import harness as h


def __getattr__(name):
    return getattr(h.ui_gate(), name)


def main(argv=None):
    parser = argparse.ArgumentParser(description='UI契約: 既存デザイン定義とbefore証跡を保存')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='command', required=True)
    capture = sub.add_parser('prepare')
    capture.add_argument('id')
    capture.add_argument('--candidate')
    capture.add_argument('--approval-ref')
    capture.add_argument('--approve-source', action='append', default=[])
    capture.add_argument('--before', type=Path)
    args = parser.parse_args(argv)
    root = args.project.resolve()
    try:
        before = json.loads(args.before.read_text(encoding='utf-8')) if args.before else []
        h.require(isinstance(before, list), 'before JSONは配列です')
        with h.exclusive(root):
            result = h.ui_gate().prepare(root, args.id, args.candidate, args.approval_ref, args.approve_source, before)
        print(json.dumps({'ok': True, **result}, ensure_ascii=False, indent=2))
        return 0
    except (h.GateError, OSError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
