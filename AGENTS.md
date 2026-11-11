<!-- codex-development-framework:start -->
## 共通開発工程（0.9.0 / ff61f89a3d28）

開発依頼では `.harness/rules.md` と `.harness/protocol.md` を読み、共通工程に従う。
指示の目的を理解し、確定要求・制約を保って最小十分に実装し、目的と元の指示の双方から検証する。
プロジェクト固有設定は `.harness/project.json`、固定版は `.harness/framework.lock.json`。
専門スキルはproject.jsonのskill_bindingsに従って使う。実スキルの接続規約は `.harness/skill-compatibility.md`。
UIの作成・変更・レビューはui_design担当を使い、既存デザイン定義を優先し、表現の過剰と不足を対等に実画面で検証する。
工程状態と証跡は `.harness/changes/`。`python3 .harness/harness.py status <id>` で確認する。
工程移行はCLIのadvanceで検証し、失敗した条件を修正する。
現在のユーザー指示と既存プロジェクト指示に従い、許可済みの作業を継続する。
<!-- codex-development-framework:end -->
