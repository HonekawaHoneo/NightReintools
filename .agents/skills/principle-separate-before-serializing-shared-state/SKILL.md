---
name: principle-separate-before-serializing-shared-state
description: "Apply when concurrent actors might write to the same file, branch, key, or state object. Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant."
---

## CodexEnvSetの接続指示

最初にプロジェクトのAGENTS指示と `.harness/skill-compatibility.md` を読み、この接続規約を上流のプラットフォーム固有の指定に適用する。
Skill専用ツールがない場合は、隣接するスキルのSKILL.mdを読む。委譲・モデル・質問・外部操作はホストの指示と利用可能なツールに従う。
pstackの既定モデルはinherit-parent。利用できないCursor・Grok・Claudeのモデル名をそのまま指定しない。

[固定した上流原本](https://github.com/cursor/plugins/blob/1e5c90a4b6f249917bd21fe361b3a2a7deb741b8/pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md)。原本の完全なコピーは同じフォルダのUPSTREAM.md。以下は上流の本文。

# Separate Before Serializing Shared State

When concurrent actors might share mutable state, first ask whether they need the same mutable object. If not, eliminate the sharing. When sharing is real, enforce serialization structurally: lockfiles, sequential phases, exclusive ownership. Instructions and conventions are not concurrency control.

**Why:** Concurrent writes to shared state create race conditions that are intermittent, hard to reproduce, and expensive to debug.

**Pattern:**
1. **Identify shared mutable state** (files both read and write, branches both push to, APIs both define and consume).
2. **Default: eliminate the shared write target.** Ask: do these actors need one canonical object, or are they publishing independent facts? Give each actor its own owned file, key, branch, or state directory, and merge only at the read/reporting boundary. Two workers writing their own `lastX` field into one `state.json` is still shared mutation. `indexer-state.json` + `metrics-state.json` is not.
3. **Only when one shared write target is a real invariant, serialize access structurally** (lockfiles, sequential phases, single-writer actor, or atomic compare-and-swap). Treat "we need a lock" as a design smell to check, not as the default answer.
