# 共通開発ルール

structural_quality.cumulativeが有効ならcumulative-quality.mdの長期基準・履歴・負債も既存工程で確認する。差分の小ささを省略理由にしない。REVIEW REQUIREDは構造修正の自動命令ではなく追加評価の要求であり、基準の更新や例外追加で自己解決しない。

回答では `.agents/skills/evidence-first-response/SKILL.md` を読み、目的・条件・根拠・実行結果を元の依頼と照合する。確認の深さは依頼に合わせ、通常の回答へ工程を展開しない。
開発では指示の目的を理解し、確定要求・制約を保って最も直接的な解決策を実行する。原指示と目的の双方向照合はprotocol.mdの既存工程で行う。具体的な確定指示を再設計へ戻さず、問題の理解とコード構造の抽象化を区別する。

1. プロジェクトルートで `.harness/framework.lock.json`、`.harness/project.json`、`.harness/protocol.md`、`.harness/skill-compatibility.md` を読み、現在の変更単位を確認する。
   structural_qualityが有効なら`.harness/structural-quality.md`を読み、実装前baselineと再利用調査、完了時の構造検査を既存工程内で行う。未設定を有効と報告しない。既存資産→最小拡張→適切な既存責務への追加→必要な新設の順に検討し、不自然な流用と不要な抽象化を避ける。
2. 既存のプロジェクト指示とユーザーの依頼に従う。許可された実装・検証・修正を継続し、同じ許可を工程ごとに取り直さない。調べられる事実は自分で調べ、要件を変える未解決の判断だけをまとめて質問する。
3. 回答は結論から短い自然な日本語で書く。通常は数行で、結果・検証・必要な判断を示す。根拠、制約、未確認事項は残す。詳細なレビュー、工程ログ、適用した原則は成果物に記録する。文書はunslopとtechnical-writingで意味を保って整え、一文一義、具体的な主語と動詞、同じ概念に同じ語を使う。依頼された詳しい説明や成果物そのものは必要な分量で示す。
4. 環境の個人プロファイルが指定されていれば、そのprinciplesを本人の判断基準として読む。私的な原則や履歴を配布リポジトリへコピーしない。AIの推測を確定した原則や権限として追加しない。モデルは親を継承し、介入・手直し・見逃しを減らすことを優先する。
5. 変更単位を `python3 .harness/harness.py new <id> --kind new|change --author <作業者ID> --context <セッションID>` で開始する。自律配送を使う場合は、先に対象のbaseを取得し、そこから `autonomy.branch_prefix + <id>` の作業ブランチを作る。既存作業を上書きせず、AI用ブランチを一つの実装者が所有する。
6. discovery、requirements、design、implementation、reviewの順に成果物を作る。工程と計画の正本はこのハーネスとし、別ワークフローで同じヒアリングや承認を繰り返さない。
7. project.jsonのskill_bindingsに指定された実スキルを使う。標準はpoteto-mode、grill-me、ponytail、ponytail-review。poteto-modeは現在の工程に必要なプレイブックだけを選ぶ。Skill専用ツールがなければ対応するSKILL.mdを読む。未提供の機能を検証済みとしない。
8. 工程移行は `python3 .harness/harness.py advance <id>` の成功で行う。失敗時は同じ工程で原因を修正する。上流変更はreopenで戻す。
9. implementationでは意味のある受入検証を登録し、`python3 .harness/harness.py run <id>` を実行する。自動修正はrunの前に行う。空の成功コマンドや未実行の結果で代用しない。
10. reviewでは、ホストが委譲を許可し別コンテキストを作れるなら、新しいレビュアーへ自動で渡す。会話履歴を複製せず、要件・設計・差分・実スキルのパスを渡す。レビュアーはコードを書かず、実際の指摘とfingerprintをreview.jsonへ記録する。同じ実装者が名前を変えて独立レビューを装わない。委譲できなければ別の人・別セッションへ引き継ぎ、不足を一度だけ報告する。
11. 重大指摘は修正してrunを再実行し、別コンテキストで再レビューする。minorの受容は理由を記載する。自律配送では、レビュアーが実際に取得したマージ先のSHAをreview.jsonのbase_shaに記録する。baseの変更後は、取り込み・検証・独立レビューをやり直す。
12. 共通ファイルは元リポジトリで更新する。独自のコマンド・スキル割当・autonomyはproject.jsonに保存する。工程を進めるためにautonomyやGitHubの保護ルールを緩めない。
13. UIの作成・変更・レビューではui_design担当（標準semantic-ui-design）とui_implementation担当（標準ui-implementation-harness）を既存工程から使う。既存の独自割当を優先し、キーがない対象は標準Skillを明示的に読む。意味・表現の判断から、同じ要件ID・meaning ID・check IDで操作・状態・実処理接続へ引き継ぐ。既存部品・Semantic Tokens・確定ルールを最初に確認し、必要な表現の不足と不要な表現の追加を対等に検証する。共有ルールを暗黙に変更せず、実画面の状態を確認する。UI契約の接続と成果物はui-design.mdに従う。

UI作業を新しく始めるときは、newの前にui schema_version=3・enforce（既存v1/v2設定は明示移行時のみ変更）、実Registry、実行可能なcheckを接続する。ui-principles.mdに従い、10原則それぞれの制作判断・期待値・実画面の観測・独立レビューを同じIDで結ぶ。文字サイズ・行高・対象寸法・余白は用途から決め、見える印と実操作領域の幅・高さを分け、全表示文はroleから独立した目的・実出典・代替・重複理由へ対応づける。励まし・装飾は文言指定のexact_textと、原依頼による明示的な制作委任のcommissioned_copyを区別する。原指示と目的・対象状態の範囲を実装前に固定し、委任された一文の再承認は求めない。不要なキャッチコピーや同義の説明を足さず、状態表示と操作結果の一致も測る。原則の適用除外・継承・寸法範囲自体・copyの目的と必要性は独立レビューで各IDへ判断を残す。モバイルや少数タスクだけで見える印を拡大せず、一般的な状態メッセージ要求だけで励ましを許可しない。設定やcheckを途中で緩めず、v1や未接続の成功を原則検証済みと報告しない。

## 自律配送

`autonomy` がない対象、またはcompletionがreviewの対象は、品質ゲートのdoneで品質確認を終える。作業成果のGit保存は次の契約を満たす。
completionがprならPR作成まで、mergedなら条件を満たしたマージまで進める。これは本人が明示的に採用した設定と現在の依頼範囲に限る。

### Gitへの保存

Gitリポジトリを対象とした実装・設計依頼の成果物（コード、設計資料、Skill、必要な工程成果物）は、そのリポジトリの管理対象パスに置き、作業ブランチへコミットし、指定リモートへ通常のpushで保存する。一時ディレクトリは作業用とし、納品物をそこだけに残さない。利用者所有の個人設定・私的原則は配布リポジトリへコピーしない。`completion=review`はPR・マージを行わない指定であり、ローカル保存だけで終える指定ではない。現在の依頼にローカル限定などの明示条件がある場合はその条件に従う。

完了報告・中断・引き継ぎの前に、保存先のリポジトリ、リモート、ブランチを確認し、コミット・push後に`python3 .harness/harness.py --json backup-check --remote origin`を実行する。originは実際の指定先に置き換える。配布元自身は`python3 runtime/harness.py --json backup-check`を使える。未コミット成果物、未push、リモートとHEADの不一致では保存済みと報告しない。remote-tracking refやpushコマンドの成功だけで代用しない。

途中版も未完了と明記して作業ブランチへ保存する。品質ゲートのdone、リモート保存、PR、マージ、環境Publishはそれぞれの実行結果で報告する。保存先が未設定・到達不能なら具体的な原因を調べ、未保存の範囲を示す。ローカルコミットをGitHub保存と呼ばない。既存の許可範囲で保存を進め、force-pushや共有ブランチへの上書きは追加しない。

1. 品質ゲートをdoneまで進める。コード・設定と必要な工程成果物をコミットし、AI用ブランチを通常のpushで保存する。force-pushは追加しない。
2. 接続されたGitHubツールが利用できれば優先する。同じheadブランチの既存PRを全状態で照合し、存在すれば再利用する。未作成の場合だけPRを作る。マージ先はbase_branchがdefaultなら対象リポジトリの既定ブランチとする。
3. PR・リポジトリの状態を直前に取得し、`ship-check <id> --forge-state <JSON>`で確認する。状態JSONの形式はcommands.mdの契約に従う。GitHub側のCLEAN、必須レビュー、CIの完了を確認し、出力されたexpected_head_shaをマージAPIに必ず指定する。接続ツールが使えずghが認証済みなら、`python3 .harness/harness.py ship <id>`が作成・照合・条件確認・マージの一回分を行う。
4. CI待機中はホストのイベント待機を使う。なければ、稼働セッション内で30秒以上の間隔を空けて状態を再取得する。shipのwaitingは完了ではない。CI失敗はログを調査して修正し、変更したコードを検証・再レビューする。必要な人の承認やGitHubの制約は迂回しない。
5. delivery.jsonへrepository、branch、base_branch、pr_number、expected_head_sha、status、時刻を記録する。状態はcreating、pr、waiting、merging、mergedを使う。マージ完了は実PRのMERGEDとmergeCommitで確認し、merge_shaも保存する。接続ツールで操作した場合も同じ契約で記録する。
6. 再開時はstatus、成果物、Git、delivery.jsonと実PRを照合する。記録の欠落や応答の消失だけでPRやマージを繰り返さない。品質のdoneと配送のmergedを区別する。最終回答は結果・検証・PRリンクを短く示す。

この仕組みはホストの稼働中セッションで進む。セッション終了後は保存状態から再開し、停止中にAIが自動で稼働すると約束しない。
