# Python構造品質ゲート（v0.5.0）

v0.7.0では[累積品質](cumulative-quality.md)を追加のopt-inで利用できる。Tach/jscpd/NetworkXを再利用し、新規解析依存は追加しない。旧Python設定と利用者のchecksはそのまま維持する。

構造検査はopt-in。工程CLIは標準ライブラリだけで動き、解析時だけ固定したjscpd/Tachとその依存を使う。MCP、Hooks、常駐サーバーは不要。

## 検査環境

検査用Pythonは3.12。工程CLIの最低要件3.10とは別。共通環境のセットアップ、またはプロジェクトの開発環境で実行する。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-quality.txt
```

解析を起動するPythonとPATHを同じ環境にする。ツールを毎タスクで自動更新しない。jscpd 5.4.0、Tach 0.35.3を固定し、更新時は固定情報と実ツールfixtureを併せて更新する。
配布元の`requirements-quality.in`が直接依存、`requirements-quality.txt`がhash付きの検査用固定情報。更新コマンドは固定情報の先頭に記録する。[効果の比較手順](quality-evaluation.md)で機械的検出とAI開発への効果を分けて評価する。

## 導入先設定

既存のtests、checks、AGENTS、native設定を調査して保持する。`examples/project-python.json`の項目を既存project.jsonへ統合し、実際のsource rootsとモジュール境界に合わせる。完成済みの設定ファイルを丸ごと置換しない。
導入済みリポジトリには`.harness/templates/`にproject-python.json、tach.toml、jscpd.json、requirements-quality.txtを配布する。必要なものだけ利用者所有の設定へ取り込み、既存ファイルがある場合は差分を統合する。共通環境の固定バンドルからも同じテンプレートを取得できる。

- `structural_quality.mode`: 初回の観測は`observe`、検証後は`enforce`。
- `source_roots`: Pythonのimport root。`clone_roots`はその内側の重複検査対象。
- `required_checks`: 必須ID。argvは検査環境のPythonと`.harness/structure.py check`。
- `jscpd_config`: 通常検出だけ。v1で受け付けるキーはminTokens/minLines/mode。
- `tach_config`: rootの`tach.toml`。root_module=forbid、ignore_type_checking_imports=false。scope内の除外は許さず、解析しない資産はroot外に分ける。
- `verification_inputs`: 検査が読む追加ファイル。Gitignore対象でも指紋へ含め、欠落・指紋除外は不合格。秘密値をログに出さない。

source roots内のPythonは実ファイル一覧と指紋を照合する。snapshot_ignoreやGitignoreで指紋から消えたファイルがあれば失敗する。検証後にそのようなファイルが追加されても完了判定を失効させる。

初期の重複閾値は50トークン・5行。行数による品質判定ではなくレビュー候補の検出条件。Tachの既存依存を許可する初期ルールはレビューして用意する。`tach sync`を検査コマンドに入れて新しい依存を追認してはいけない。

## 変更の進め方

設定を用意した後、実装前に実行する。

```sh
python3 .harness/harness.py new feature --kind change --author builder --context session --base BASE_SHA
python3 .harness/harness.py baseline feature
```

BASE_SHAは実際のマージ先コミットに置き換える。Gitが空・存在しない場合だけ基準なしを許し、Git比較は未実施とする。既存の未コミット作業を含む開始状態を保持する。

baselineはdiscovery中に一度だけ取得する。開始時からソース・設定が変われば取り直せない。baselineの失敗は原因を直して新しい変更単位で開始し、現在の実装を過去の状態として承認しない。

1. discoveryには`reuse_candidates`を記録する。各候補はpath、symbol、decisionを持つ。候補ゼロなら`reuse_search`に検索範囲と結果を書く。
2. designの`impact_paths`を編集予定、`affected_paths`を影響確認対象とし、`new_module_reasons`へ新設の理由を残す。
3. 編集ごとの全解析は行わない。実装後の`run`で、必須構造検査と既存の受入検証を行う。
4. 別コンテキストのreviewで`structural_review`のreuse、semantic_duplication、responsibilities、dependencies、simplicity、impactの各根拠を記録する。
5. 明白な新規違反を直し、再run・再レビューする。同じ原因で2回失敗したら前提・技術選択・構造を見直す。

既存の循環・重複は基準として記録し、新規または拡大を不合格にする。循環はnative mapからNetworkXで比較し、メンバーと内部edgeの増加を検出する。旧循環のメンバー・辺の部分集合へ縮小・分割する改善は許容する。Gitで一意に対応する改名は再同定候補として記録し、責務が同じことを独立レビューで確認する。

## 証跡とCI

baselineはnative JSONを既存evidenceログへ保存し、そのハッシュをdiscoveryへ結び付ける。結果の対象はソース指紋・成果物・コマンド・解析条件・固定Git基準で識別する。OS、Python、ツールの実体と版は実行記録として保存する。

ローカルのcheckはツール変更も検出する。CIの事前checkはローカル実行環境との一致を要求せず、同じ対象・方針を確認してからCI自身で再実行する。HEADだけの変化をソース変更と混同しない。

```sh
python3 .harness/harness.py ci --base BASE_SHA
```

CIはGit差分のreview.jsonから変更IDを1件選ぶ。0件・複数件は拒否する。基準SHAは開始記録・レビューと一致し、HEADの祖先である必要がある。コード・設定をコミットしてから実行する。ローカル開始前からあった変更もPR全体のGit比較で検査する。

`examples/project-ci.yml`と`examples/CODEOWNERS`を導入先に合わせる。本人がGitHubで以下を設定・実確認するまで、強制導入完了とは呼ばない。

- 必須status check `verify`、最新baseへの追従、保護の迂回禁止。
- ゲート・workflow・CODEOWNERSの変更に対するcode owner保護。
- `quality-policy` environmentの本人reviewer。必要な承認権限をAIへ渡さない。
- 弱化検出処理を保護し、PR自身が承認済みと記録して通せないこと。

policy_changes.pyは除外拡大・検査削除・閾値緩和を列挙するだけで承認しない。曖昧な境界方針の変更やゲート実装の変更も本人へ回す。通常のアプリ変更、検査追加、単純な閾値強化は承認対象にしない。
ソース内の`tach-ignore`も例外として扱う。標準tokenizeで抑制対象の論理文を識別し、新規・適用先変更・複数行の適用拡張を承認対象にする。同じ文の行移動と例外削除は弱化にしない。CIの必須verifyは前提ジョブが失敗・拒否・取消になっても起動し、明示的に失敗する。

## 保証の限界と更新

Python構文の検証は標準パーサー、依存抽出はTach、重複抽出とfingerprintはjscpd、循環計算はNetworkXへ委ねる。独自のソース解析エンジンを持たない。Tach CLIが孤立ノードを省くため、同じnative engineを各ファイルにも実行して取り込み範囲を確認する。

動的import・reflection・意味的重複は網羅できない。同じcloneパターンの場所だけの移動もbaselineが同一視する場合がある。関連コードを含む意味レビューと既存テストで補う。サイズ・複雑性の数値だけでは停止しない。

observeで違反があっても、解析不能・対象漏れ・ツール欠落は失敗。observe成功を構造違反ゼロと報告しない。enforceからの降格・例外追加・除外拡大は本人承認を要する。

0.4.0からは明示更新する。導入済みのユーザー設定・独自checks・過去のdoneは保持し、新機能は勝手に有効化しない。導入変更を独立コミットにし、戻すときはその変更だけをrevertする。管理ファイル削除を伴う旧版再インストール、ユーザー作業を消すresetは使わない。
