---
name: grilling
description: "Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases."
---

## CodexEnvSetの接続指示

最初にプロジェクトのAGENTS指示と `.harness/skill-compatibility.md` を読み、この接続規約を上流のプラットフォーム固有の指定に適用する。
Skill専用ツールがない場合は、隣接するスキルのSKILL.mdを読む。委譲・モデル・質問・外部操作はホストの指示と利用可能なツールに従う。
pstackの既定モデルはinherit-parent。利用できないCursor・Grok・Claudeのモデル名をそのまま指定しない。
調査と要件工程で、未解決の意思決定を質問する。環境の事実は調べ、回答済み・許可済みの事項を再度承認待ちに戻さない。判断をdiscovery.jsonとrequirements.jsonへ記録する。 ../requirements-discovery/SKILL.mdを読み、protocol.mdの原指示と目的の契約を既存成果物へ接続する。

[固定した上流原本](https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/grilling/SKILL.md)。原本の完全なコピーは同じフォルダのUPSTREAM.md。以下は上流の本文。

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
