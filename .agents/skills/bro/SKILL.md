---
name: bro
description: "Restate the last message in plain human language, with no jargon."
---

## CodexEnvSetの接続指示

最初にプロジェクトのAGENTS指示と `.harness/skill-compatibility.md` を読み、この接続規約を上流のプラットフォーム固有の指定に適用する。
Skill専用ツールがない場合は、隣接するスキルのSKILL.mdを読む。委譲・モデル・質問・外部操作はホストの指示と利用可能なツールに従う。
pstackの既定モデルはinherit-parent。利用できないCursor・Grok・Claudeのモデル名をそのまま指定しない。

[固定した上流原本](https://github.com/cursor/plugins/blob/1e5c90a4b6f249917bd21fe361b3a2a7deb741b8/pstack/skills/bro/SKILL.md)。原本の完全なコピーは同じフォルダのUPSTREAM.md。以下は上流の本文。

Restate your last message. Stop using jargon and speak coherently. State it more simply and concisely, like one human talking to another.
