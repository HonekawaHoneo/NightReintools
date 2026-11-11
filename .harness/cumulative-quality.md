# 累積した構造品質の管理

v0.8.0でmainへ統合した追加opt-in。既存のPython構造検査・工程・receiptを使い、小変更でもGit履歴と承認済み基準を照合する。配布元はまず累積observeで観測し、既存native検査のenforceは維持する。長期的な効果と閾値の較正は後続の評価対象。

## 既存機能の再利用

構造・境界はTach 0.35.3、重複とfingerprintおよび複雑性はjscpd 5.4.0、循環と変更結合はTachの既存依存NetworkXへ委ねる。新しい解析エンジン・DB・常駐処理・MCP・Hooksを必須にしない。requirements-quality.txtは変更しない。

jscpdの複雑性はnativeのtokenベースの観測値。ファイルごとの基礎値1を除いた増分を責務群へ合計し、最大値・tokens・lines・依存先も保持する。精密なMcCabe値や意味的な難しさとは同一視しない。関数分割だけで品質改善と認定しない。

変更結合はGit取り込みと責務の二部グラフをNetworkXで射影する。共起数とJaccard値を分けて記録する。同時に変更されたことは、構造劣化や因果関係の証明ではない。

## 初期化と設定

既存のproject-python.jsonは変更しない。追加用のproject-cumulative.jsonをテンプレートとして配布する。導入済みプロジェクトのchecks等を保持し、必要な部分だけ統合する。

1. 既存のsource_roots・clone_roots・Tach境界を確認する。新規Gitプロジェクトは、まず比較できる初期コミットを作る。
2. 次のコマンドで候補を出す。既存の方針は上書きしない。

```sh
python3 .harness/structure.py policy --base BASE_SHA --project-id PROJECT_ID > candidate-quality-policy.json
```

3. 候補のresponsibilitiesを実際の責務ID・paths・purposeへ編集する。全Pythonソースを一つだけの責務へ対応づける。生成したpurposeの空欄を埋め、単なる技術ディレクトリを業務上の責務と決めつけない。
4. 初期化する新しい方針を`.harness/quality-policy.json`へ保存し、project.jsonへ次を統合する。

```json
"cumulative": {"mode": "observe", "policy": ".harness/quality-policy.json"}
```

上記はstructural_quality内の項目。方針ファイルをverification_inputsにも入れる。既存Gitでshallow・基準不在・非祖先の場合は失敗とし、履歴ゼロの成功にしない。

adopted_shaは導入時のコード、anchor_shaは承認した設計基準。quality_policyのanalysis_digestはnative条件・固定版・接続/判定コードに結ぶ。ツール・解析設定・接続実装の更新で不一致が出たら、同じ契約だったことにせず明示更新する。

## 比較と記録

今回の開始baselineとPR base、直近20取り込み、直近90日、承認済みanchor、導入時の負債を分ける。履歴の回数単位はfirst-parentの取り込み。merge配下のコミットを二重に数えない。期間窓の日付はGitのbase日時を基準とし、常駐・カレンダー監視ではない。

構造の測定点は導入時・anchor・各窓の開始直前・base・現在。既存scanを同じ固定条件で実行し、全commitを観測したとは扱わない。nativeの対象漏れ・欠測はゼロにしない。

履歴manifestはcommit/treeと固定メタデータのGit blobに結ぶ。過去のdesign/review/stateはbaseから読み、作業ツリーのlatest.jsonで差し替えない。履歴証跡がない場合もGit sourceを再測定できる。測定は現在の固定条件で正規化した値であり、当時の条件による観測とは区別する。

再評価の省略に使う確認点は、固定された実行receipt・登録checks・成功結果・ログのblob/hash・解析とレビューのsubject/policy/groupの一致を確認する。工程形式ではレビューのコード/成果物指紋も照合する。完了フラグだけの古い記録は背景情報には残すが、確認点にしない。単独scanも実行ログとanalysis.jsonをreceiptへ結ぶ。

純粋なGit改名は一対一の対応候補として利用する。分割・統合の責務IDは利用者所有の方針へ保持し、旧新パスの両方を対象に残す。曖昧な移動を既存負債の免責にしない。未知の責務や比較不能な解析は合格にしない。

既存負債は導入時snapshotのnative識別子とunitsから扱う。新規・拡大・観測した解消後の再発をBLOCKにし、既存負債が残るだけでは停止させない。未観測区間での解消・再発は断定しない。旧処理の意味や不要な互換処理の網羅的発見は独立レビューが担当する。

## 深掘りの条件

初期閾値は次の観測仮説であり、効果検証済みの品質定数ではない。

- 同じ責務の4回以上の変更と、複雑性増分5以上かつ20%以上、または依存先2つ以上の増加。
- anchorから複雑性増分10以上かつ25%以上。
- 共起5回以上、Jaccard 0.6以上、前窓から0.15以上の増加。
- 同じ明示された根因について過去2件と現在の回避処理が関連する。
- 最後の全体レビューから20取り込みまたはGit日時で90日。

数値やAIの推測だけでBLOCKにしない。REVIEW REQUIREDで、局所修正・限定した構造整理・設計変更を比較する。新規のnative構造違反や観測済み負債の再発は、意味的な説明だけで解除しない。

## 既存工程への追加

baselineはdiscoveryで実行し、再利用・影響確認とともにcumulativeのfindings/scope/historyを読む。毎回ログ全体をモデルへ投入せず、所見・関連責務・必要な測定点を参照する。

designには以下を記録する。

- responsibility_changes: id、requirements、reason。実際に変更する責務を含める。
- root_causes: 通常は空配列。原因を扱うときはid、paths、reason、checks、workaroundを持ち、回避処理にはremoval_conditionも必要。
- legacy_paths: 旧実装・互換処理の確認対象パス。通常は空配列。

runはREVIEW REQUIREDでも解析成功として記録し、implementationからreviewへ進める。enforceのreviewにはcumulative_reviewを追加する。

| 項目 | 必要な値 |
| --- | --- |
| subject_digest / policy_digest | 今回のcumulative出力の値 |
| scope / group_digests | 確認した責務と同じ構造状態。要求されたscopeを含める |
| whole_design_review | 全体再評価の所見がある場合はtrue |
| alternatives | local_fix / scoped_refactor / design_changeの比較理由 |
| behavior_checks | receiptで成功した、構造検査以外の検証ID |
| dispositions | 所見IDごとのexplained / resolved / deferred、理由と実在コードの根拠 |
| legacy_dispositions | legacy_pathsごとのremoved、またはretainedの理由と終了条件 |

延期できるのは追加評価の所見。owner・removal_condition・1〜20取り込みのreview_after_changesを要求し、期限到達時に再評価する。重大なnative違反は延期でPASSにしない。

期限の所見には安定した義務IDを使う。後続の証跡付きレビューで解決・説明された義務は閉じ、再延期された場合は新しい期限を使う。解決済みの古い延期を永続的に要求し続けない。

同じ構造状態の確認点は次回の追加評価に再利用するが、現在のコードへの通常レビューとcumulative_reviewは省略しない。新しい悪化では再起動する。全体レビューの周期だけを確認点から数え直し、anchor・導入履歴・負債の許可は更新しない。

## 単独scanとCI

配布元のquality.jsonと、導入先のharness run/ciは同じ累積評価を使う。単独scanのenforceも未解消REVIEWを失敗にする。

```sh
python3 runtime/structure.py scan --config quality.json --base BASE_SHA > report.json
python3 runtime/structure.py scan --config quality.json --base BASE_SHA --review .harness/changes/quality-review/review.json
```

--reviewでは登録した挙動checksを既存の共通実行器で実行し、コード・レビューの変化と非0終了・timeoutを拒否する。出力証跡は`.harness/changes/scan-<token>/evidence/`に置く。説明JSONだけで挙動検証を実施済みにしない。

observeは品質所見を残して完了できるが、raw BLOCK/REVIEWを品質PASSと表示しない。元のstructural_quality.mode=enforceは弱めない。未実施・対象不正・解析契約不一致はobserveでも拒否する。

基準更新は新epochとpreviousの固定commit/pathを持ち、実際のbaseにある旧方針へ結ぶ。adopted_shaを変更して過去を消せない。旧ソースの正規化測定と全体レビューで比較し、異なる条件での値をそのまま連結しない。基準更新の方針変更は実装前に準備し、新しい変更単位から検証する。

方針ファイルの移動時もbaseの設定から旧パスをたどる。移動を初回導入として扱って導入履歴をリセットしない。

policy_changes.pyは方針の追加・削除・基準/責務/解析条件の更新・閾値緩和を列挙する。明示した閾値の単純強化以外は所有者の確認対象。保護されたbase側の検出器を使い、GitHubのquality-policy environment、CODEOWNERS、必須チェックと迂回禁止を本人が設定するまで強制導入完了とは報告しない。ローカルJSONと作業者名は署名監査や悪意ある改竄に対するセキュリティ境界ではない。

## 社内業務での利用条件

今回確認した用途は、社内業務でハーネスを使い、その応答と業務用アプリを作成すること。社内利用を一律に非商用とは扱わず、業務利用可能な条件で選択した。

新しい第三者依存は追加していない。固定配布物のjscpd 5.4.0とTach 0.35.3のMIT許諾文、NetworkX 3.7のBSD-3-Clause、および既存固定環境の推移依存のMIT/BSD表示を確認した。既存スキルの上流原本・ライセンス・固定ハッシュも維持する。

この用途のためにGitNexusのNoncommercial条件、DesloppifyのOSNL、商用サービス契約、Code MaatのGPL等を追加で持ち込まない。今回の追加機能に、生成した応答・アプリの公開義務を課す新しい依存を導入していない。将来のアプリへ別の素材や依存を取り込む場合、その対象の条件は別に確認する。

参照: [固定版jscpdの機能](https://github.com/kucherenko/jscpd/blob/v5.4.0/docs/rust.md)、[MIT許諾文](https://github.com/kucherenko/jscpd/blob/v5.4.0/LICENSE)、[Tach](https://github.com/tach-org/tach)、[NetworkXのJaccard射影](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.bipartite.projection.overlap_weighted_projected_graph.html)、[BSD許諾文](https://github.com/networkx/networkx/blob/networkx-3.7/LICENSE.txt)。機能説明だけでなく、今回取得した固定版の実出力と配布物のLICENSEを照合した。

## 検証の境界

回帰試験はGit/merge/rename、正常な反復と累積悪化、既存負債、観測済み再発、根因参照、epoch更新、未実施/古い証跡、observe/enforce、実native出力と工程遷移を確認する。架空のレビューJSONを使う試験は形式的なゲートの試験であり、独立AIレビューの実績ではない。

当初のA-JによるAI比較、意味的な責務混在・根本原因の検出率、誤検出、長期の有効性、処理時間・トークンの較正は後続。[評価手順](quality-evaluation.md)へ記録し、未測定の効果を実証済みとはしない。
