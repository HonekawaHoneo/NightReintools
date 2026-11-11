# Semantic Component-Driven UI Design — 共通契約とv1互換

新規UI作業には[原則の検証契約v2](ui-principles.md)を使う。この文書は既存Registry・設計・runner・receiptの共通部分とv1の互換契約を説明する。v2の追加条件はリンク先を優先する。v1の成功を10原則の検証済みと扱わない。

## 採用する構成

既存の共通工程にUI専門Skillと任意の検証契約を加える。工程管理、検証runner、独立レビュー、版固定配布は再利用する。対象はUIの意味、配置、視覚的階層、奥行き、部品、状態、密度、アクセシビリティ。アプリ内部の責務分離やバックエンド設計は担当しない。

同じ役割でも対象・状態・重要度・危険性・文脈は分離する。装飾の少なさや美しさは独立の目的にせず、必要な意味を伝える表現の十分性で評価する。名前、業務データ、必要なラベル、警告、アクセシブルネームを保つ。

## 現環境との差分

- ponytailの既存部品優先、Experience First、Prototype、既存の独立レビューを再利用する。
- Visual parityは外観を維持する移行だけに適用する。意味を改善する変更に差分ゼロを要求しない。
- Subtract Before You Addは実装・工程の複雑性を減らす原則。必要な階層や状態表示の省略を正当化しない。
- 汎用カタログ生成、DB/MCP、フレームワーク解析、Storybookの新設は初期版に含めない。

## プロジェクト設定とRegistry

`.harness/project.json`の任意の`ui`は`schema_version: 1`、`mode: observe|enforce`、`registry`（相対パス）、`input_globs`（UI入力のglob配列）、`check_ids`（登録済みcheck ID配列）を持つ。未設定の旧対象は従来どおり。Skill割当は`ui_design: semantic-ui-design`。

globはプロジェクトからの相対パスで、`*`・`?`・文字クラスは一つのパス要素、`**`は0段以上の階層に一致する。`src/**/*.tsx`は`src/App.tsx`も対象とする。既存ディレクトリの影響宣言も内部の対象を検査する。brace展開は未対応で設定エラーにするため、tsxとcssなら二つのglobを指定する。

RegistryはJSONで`schema_version: 1`、`components`と`tokens`の配列を持つ。各componentは`id`、`source_ref`、`meaning`、`use_when`、`relations`、`token_ids`、`required_cues`、`optional_cues`、`avoid`、`a11y`を持つ。配列は必要に応じ空にできる。`variants_ref`と`states_ref`は既存定義への任意の参照。各tokenは`id`、`source_ref`、`meaning`を持つ。

`relations`は`{kind, component}`の配列で部品間の関係と相手IDを指定する。例えばツリーの開閉操作が既存buttonを使う場合は`{"kind":"uses","component":"button"}`。相手IDの存在は機械検査し、関係の意味はレビューで確認する。

共有stylesheetなど、部品の参照先以外にも確定ルールを所有する定義元があれば、Registryの任意`sources`参照配列へ登録する。参照グラフを自動推測する仕組みは作らず、登録した定義元の変更を検出する。

参照は`{"path": "プロジェクト内の定義", "pointer": "/optional/json/pointer"}`。pointerは既存JSON定義を直接参照し、variants/statesは文字列配列を解決する。非JSONの実装はpathだけで参照し、公開APIの詳細は既存lint/testsとレビューで照合する。トークン値やAPIをRegistryへ手コピーしない。必要な意味情報だけを補完する。参照切れ、重複ID、不明token、無効なJSON pointerは拒否する。必須cueは、変更する部品の判断全体で網羅する。cueの申告と実画面での識別可能性は別に検証する。

## 設計契約

`python3 .harness/ui_contract.py prepare <id>`は現在Registryと定義元の指紋を変更単位内へ保存し、`registry_snapshot`用の`path`と`sha256`を返す。既存UIのbefore画像は既存ブラウザで実装前に取得し、`--before <JSON>`で渡す。各項目は`scenario`、`path`、後述の`environment`を持つ。これは証跡記録であり画像取得や工程移行は行わない。

承認されたRegistry改定案は`--candidate <JSON> --approval-ref <実際の承認参照>`で渡す。共有定義元を変更する場合は`--approve-source <path>`を追加する。承認参照は権限を自動証明する署名ではない。独立レビューで実際の承認と変更内容を確認する。設計時は保存した変更前定義と予定Registryを検査し、実装時は現在Registryが予定と一致し、定義元の変更が承認範囲内であることを検査する。検証のために承認済み設計を書き換えない。

承認済み定義元へ新variant/stateを追加する場合、設計時は未実装の選択肢を許し、実装後・証跡受理前に実際の定義へ厳密に照合する。未実装のままでは合格しない。定義元の削除は、そのパスが明示承認され、予定Registryからも参照が除かれた場合だけ許す。現在も参照される定義元は存在を必須とする。

`design.json.ui`:

- `scope: none|local|shared`と`reason`。UI入力・Registry・定義元への影響と照合し、UI変更をnoneにできない。
- `registry_snapshot: {path, sha256}`（noneでは不要）。
- `meanings: [{id, requirement, meaning}]`。既存要件IDと対応させる。
- `decisions: [{meaning, component, cues, omitted, tokens, variant?, state?}]`。`omitted`は`{cue, reason}`の配列。全meaningを一度ずつ対象にする。
- `scenarios: [{id, meanings, check, preview, baseline, reason}]`。baselineは`existing|new`。全meaningをカバーし、既存画面の各scenarioにはbefore画像が必要。新規画面は理由を記録する。

全DOM要素を台帳化せず変更する意味的なまとまりだけ記録する。localは変更状態・配置先・同役割比較、sharedは登録された利用先へ検証を広げる。関連先を絞れない場合は登録済み代表画面全体を見る。

## 実行証跡とレビュー

UI実装は`ui-implementation-harness`の契約索引へ、design.json.uiの要件・meaning ID、scenarioのcheck IDと確定改訂を参照として引き継ぐ。同じ意味や定義を別の正本へコピーしない。接続ごとのmock/partial/unimplemented/productionと検証範囲を保持し、視覚レビューの合格だけで実保存・認可・OS接続を実装済みとしない。プロジェクトの独自Skill割当は維持する。

既存runnerが各checkへ`CODEXENVSET_CHANGE_ID`、`CODEXENVSET_CHECK_ID`、`CODEXENVSET_EVIDENCE_DIR`を渡す。保存先は実行とcheckごとに分離し、別providerの同名画像を上書きさせない。既存checkの非0終了・timeout・ソース変更拒否は維持する。

UI providerは出力先に`<check-id>.ui.json`を生成する。形式は`{"schema_version":1,"scenarios":[{"id":"...","status":"passed|failed|not_verified","observations":"実測の説明","files":[{"path":"出力先からの相対パス","kind":"screenshot|aria|trace|metrics"}]}]}`。各scenarioに実画面のscreenshotと、`viewport`、`browser`、`theme`、`fixture`を含む`environment`を記録する。固定条件で取得し、重要な状態をmaskしない。

報告と添付のハッシュを既存receiptへ記録する。画像の欠落・改変、古い入力、無効な契約は検出対象。機械検査の成功だけで意味の分かりやすさやWCAG適合を主張しない。

`review.json.ui`は`receipt_ref: {path, sha256}`、`checked_scenarios`、`observations: [{scenario, understood, excess, missing, assessment}]`、`status: passed|request_changes|not_verified`を持つ。understoodは観測できたmeaning IDの配列、excess/missingは具体的所見の文字列配列。独立レビュアーは先に画面・操作から意味を回答し、その後設計と照合する。特定の成功receiptを参照し、CI再実行で新しい画像へすり替えない。

observeでは品質違反や未確認をそのまま記録して導入を観測する。報告作成の成功とUI合格は別。enforceではシナリオ不足・未確認・品質違反・視覚レビュー不足を完了条件として拒否する。契約不正、証跡改変、既存検証失敗は両モードで拒否する。

## 評価と導入

最初に深いツリーと既存ボタン変更で接続を確認し、タスク一覧、削除、設定、アイコン、簡素化、表現不足の改善へ広げる。装飾数や占有率で採点しない。親子・兄弟・現在位置・展開可能性・選択とフォーカス、操作発見、状態、再利用、不要な新設、操作手順を評価する。

WCAG 2.2 AAを基準に機械検査と視覚・操作レビューを併用する。画像差分は変化を検出する道具であり改善の正しさの判定器ではない。48生成比較と利用者調査は効果検証段階で実施し、未校正の数値を初期導入の必須条件にしない。

共有ルールの例外は範囲、理由、管理者、期限と代替手段を残す。工程を通す目的で検証モードを緩めない。切り戻しはUI導入設定の差分だけを管理者が戻し、利用者設定・Registry・成果物を保持する。既存installerによる自動downgradeは前提にしない。

## 参照

- [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)と[Skills](https://learn.chatgpt.com/docs/build-skills): 最小の常時指示と専門手順の分離。
- [Atlassian Design Tokens](https://atlassian.design/foundations/tokens/design-tokens/): 値の一致ではなく意味から選択する。
- [Carbon Tree View](https://www.carbondesignsystem.com/building-blocks/core/components/tree-view/guidelines)と[Data Table](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines): 情報の意味と作業に応じた部品選択。
- [WAI Tree View](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)、[WCAG 2.2](https://www.w3.org/TR/WCAG22/)、[評価ツールの限界](https://www.w3.org/WAI/test-evaluate/tools/selecting/): 状態・操作・自動化できない確認。
