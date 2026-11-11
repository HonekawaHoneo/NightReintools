# UI原則の検証契約 v2/v3

原則を制作判断、実画面の観測、独立レビューへ同じIDで結ぶ。意味の伝わり方や文章の必要性を機械が保証する契約ではない。機械は欠落・参照切れ・期待値との不一致を拒否し、意味の妥当性は実画面を見た独立レビューが確認する。

## 接続と互換性

新規UI作業は変更単位の`new`前に、実行可能なcheckと以下の設定を用意する。pathとコマンドは対象アプリの実物に合わせる。

```json
{
  "ui": {
    "schema_version": 3,
    "mode": "enforce",
    "registry": "ui/registry.json",
    "input_globs": ["ui/**"],
    "check_ids": ["ui-browser"]
  }
}
```

Registry自体のschema_versionは1。既存の意味・部品・scenario・before画像・runner・receiptの形式は[UI契約](ui-design.md)を引き継ぐ。v2では下記の基本契約、v3では末尾の追加契約を適用する。既存v1/v2設定・check・証跡は自動移行しない。

v2/v3のui設定と参照するcheck定義は`new`で固定する。途中の削除、v1化、v3からv2への降格、observe化、glob縮小、check差し替えは拒否する。接続の変更は理由を明示して新しい変更単位で行い、同じ品質成功として証跡を流用しない。既存v1設定をinstallerが自動で変更することはない。v1の合格とv2の原則検証を区別して報告する。

既存v1や未設定の対象でUI作業を始める場合も、要件に必要な検証を調査して新しい変更単位でv3へ明示接続する。既存の進行中変更へ設定だけを差し替えない。接続できていないなら未検証と記録する。

初めてUIを作る場合は、先に`schema_version: 1`と空の`sources/components/tokens`配列を持つRegistryを用意する。`new --kind new`で開始し、ワイヤーフレームをinputsへ保存してから、非空の予定Registryを`prepare --candidate <JSON> --approval-ref <依頼・承認の参照>`へ渡す。予定する定義・実装ファイルは新設参照として遅延解決できる。空Registryのまま候補なし・承認参照なしでは進めず、実装後には予定Registryと参照先の実在を必須とする。すでに依頼で許可された範囲はその依頼を参照し、同じ承認を取り直さない。既存UIでこの空baseline経路を使わない。

## 実定義と制作判断

部品の`implementation_ref: {path, anchor}`はUI入力の実ファイルと非空の箇所を指す。部品の`source_ref`は`{path, pointer}`または`{path, anchor}`で非空の定義を指す。トークンのsource_refは`{path, pointer}`で具体的なJSON scalar値を指す。空ファイル、null、空の配列・オブジェクト・文字列、pathだけの名札はv2では使えない。各部品のtoken_idsと採用するdecision.tokensを空にしない。tokenは実装で使うデザインシステムのJSON値を参照する。CSS宣言のanchorを数値へ暗黙変換する機能は持たない。承認済みcandidateによる新設参照は既存prepareの遅延解決を使い、実装後に実在を要求する。

`design.ui.principles`は次の10 IDを重複なく持つ。各項目は`id, status, decision, source_refs, case_ids, details`。statusは`applicable|inherited|not_applicable`。継承でも既存定義の実在参照と観測caseを必要とする。視覚UIの基本原則を非適用にして検査を飛ばせない。操作のない画面ではstates_actionsを理由付きで非適用にでき、独立レビューで確認する。

| id | detailsで決める内容 |
| --- | --- |
| meaning | primary_action、objects、states、risks、case_ids。対象・操作・状態・危険性を分ける |
| structure | wireframe_ref、groups。groupはid、members、comparison_axis、primary_action_location。実装前のワイヤーフレームをprepareより先に変更単位のinputsへ保存し、hashを固定する |
| reuse | components。各項目はcomponent、existing_ref、standard_alternative、choice（reuse/new）、reason、difference、uses。既存→組み合わせ→バリエーション→新設を検討する |
| visual_hierarchy | order、reason、case_ids。情報・操作の優先順位を作業に合わせる |
| tokens | bindings。各項目はtoken、target、case_ids。採用tokenを同じ対象の実測assertionへ結ぶ |
| density_typography | measurements。dimension（font_size/line_height/row_height/target_size/spacing）の5種類、target、purpose、case_ids。caseは同じ対象の数値range |
| copy | items、inventory_case_ids。各itemはtext、role、requirement、reason。詳細は下記 |
| states_actions | consistency_case_ids、actions。操作のentrypoint、6種類のoutcomes。詳細は下記 |
| accessibility | checks。aspect（label/keyboard/focus/width/zoom/reading_order/operable_targets）、target、case_idsを全種類。assertionで実操作・観測を結ぶ |
| scope_connections | changed、related、state_owner、connections、boundaries、complexity。接続はentrypoint、handler_ref、status（mock/partial/unimplemented/production）、case_ids |

dimensionの数値は用途別に決める。小さな操作アプリは通常の本文と控えめな見出しから始め、読み取り・操作・所属を示すために必要な寸法を選ぶ。例の24px上限はそのタスク画面の設計値であり、すべてのアプリを24px以下にする規則ではない。独立レビューは範囲自体の妥当性も確認する。

copyのroleは`name|data|label|status|error|explanation|decoration`。説明・装飾には、配置・状態・短いラベルで代替できない理由`alternative`と、明示的要件や既存仕様への`source_ref`も必要。励ましやキャッチコピーを雰囲気だけで追加しない。空・エラー・全件完了の案内も、必要な状態と次の操作を短く示す。itemsの順序が実画面の表示文一覧の順序になる。状態ごとに文が違う場合はitemの`case_ids`で所属するinventory caseを指定する。省略時は全inventory caseへ含める。動的データはscenarioの固定fixtureで具体値を決める。全表示文を対象にし、余分な文を除外するために取得対象を狭めない。

actionsの各項目は`id, entrypoint, outcomes`。outcomeは`success|failure|cancel|duplicate|late_response|focus`を一つずつ持ち、`applicable`（boolean）、`reason`、`case_ids`を記録する。適用される結果にはassertion caseが必要。非同期処理のない操作でlate_responseを非適用とする等、事実に基づいて判断する。未実装や未検証を非適用へ置き換えない。進捗の文字とバー等、複数表示の状態が一致することも測る。

トークンの実測値は定義値と型・単位をそろえて比較する。数値rangeへ結ぶtokenはJSON数値を必要とする。色の表記変換などは対象の既存デザインシステムまたはproviderで一貫して行い、Registryへ定義値を手コピーしない。

寸法のcaseは異なるdimension間で使い回さない。例えばfont_sizeの一つの測定値をline_height・row_height・target_size・spacingにも割り当てて、必要な観測を省くことはできない。

## Caseと実測値

`design.ui.cases`は全scenarioと適用原則・採用tokenをカバーする。各項目は`id, scenario, principles, kind, question, target, tokens`。原則のcase_idsと双方向に対応する。

```json
{
  "id": "task-heading-size",
  "scenario": "tasks-desktop",
  "principles": ["tokens", "density_typography"],
  "kind": "assertion",
  "question": "タスク画面の見出しが設計した文字サイズか",
  "target": "main h1",
  "tokens": ["task.heading.size"],
  "expectation": {"operator": "range", "min": 20, "max": 24}
}
```

assertionのexpectationは`{operator: equals, value: JSON値}`または`{operator: range, min: 数値, max: 数値}`。有限数のみ、booleanと数値等は区別する。copyのinventoryは該当items.textの配列とのequals。visualは画面で答える具体的なquestionを持ち、機械判定の代わりには使わない。取得成功はcase_results.status=observedであり、意味の合格ではない。token照合と寸法、適用操作結果はassertionを必要とする。

providerのschema_versionを2にし、既存scenario報告へ`case_results`を追加する。

```json
{
  "id": "task-heading-size",
  "observation": "幅1280pxの画面でh1のcomputed font-sizeを取得",
  "value_ref": {"path": "metrics.json", "pointer": "/heading/fontSize"}
}
```

value_refは同じscenarioのfilesに登録したmetrics/aria/traceのJSONを指す。スクリーンショットも必要。ハーネスがファイル内のactualを取り出してexpectationと比較する。providerがpassedを返しても、不一致はUI合格にならない。空観測、欠けたcase、重複、不正なpointer、別scenarioの添付への参照を拒否する。ファイルと報告のハッシュ・ソースの鮮度は既存receiptで検査する。

CSS宣言の文字列を読むだけで実寸法を測定したことにしない。computed style・bounding box・全可視文字・操作後の状態等を既存ブラウザ手段で取得する。固定fixture、viewport、browser、themeを記録し、必要な幅・拡大・状態をscenarioへ分ける。provider自体が正しく観測しているかもレビュー対象。

## 独立レビューと完了条件

`review.ui`の既存receipt_ref・scenario観測に加え、`principles`へ全10項目を記録する。各項目は`id, case_ids, observations, status, excess, missing`。statusは`passed|request_changes|not_verified`。case_idsは設計と一致させる。observationsは原則別に、実測値・画面上の位置・操作と結果を挙げる。共通の「確認した」文で埋めない。

レビュアーは実装者と別のコンテキストで、画面・操作から読み取れた意味を先に記録してから設計へ照合する。必要な手掛かりの不足と、不要なコピー・拡大・余白・装飾を対等に調べる。適用除外、継承、期待値の妥当性、mock等の未接続も確認する。

enforceは不足・未検証・失敗・未解決の過剰/不足をdoneの拒否条件にする。observeは品質結果を記録するが合格を意味しない。どちらでも契約不正や証跡改変は拒否する。これらは実行の自己申告を無条件に信頼しないためのゲートであり、悪意あるprovider、機械では判断できない文意、初見利用者の理解やWCAG全面適合を証明する仕組みではない。

実行例は配布元の`examples/ui-principles/`。実Chromiumで正常例と余分なコピー・43px見出し・1/1なのに33%の進捗を測り、providerのpassed申告があってもゲートが不一致を拒否する。正常例も独立レビューを捏造せずreviewで停止する。


## v3：見える寸法、実起動領域、copyの根拠と期待値の妥当性

v3は上記v2をすべて継承する。同じrunner、snapshot、receipt、reviewを使い、追加の承認工程を作らない。providerのschema_versionも3とする。既存v2のnative例は既定の呼び出しで引き続き検証できる。

`density_typography.details.measurements`の全項目に一意の安定した`id`を付ける。5種類のdimensionは維持する。さらに`controls`を追加する。

```json
{
  "id": "task-toggle", "action": "toggle",
  "visual": {"target": "#task", "width_case_ids": ["mark-width"], "height_case_ids": ["mark-height"]},
  "hit": {"target": ".task-label", "width_case_ids": ["hit-width"], "height_case_ids": ["hit-height"]},
  "activation_case_ids": ["activate-from-padding"],
  "reason": "本文に合う控えめな印と、独立に確保した操作領域"
}
```

各寸法caseは同じtargetの数値range assertionとし、`dimension`を`width|height`にする。幅・高さを一つの観測で兼ねず、各領域・軸につきscenarioごとに1つ測る。visualとhitのselectorが同じ通常ボタンは、同じ軸のcaseを共有できる。異なる軸は別caseが必要。四つの軸とactivationのscenario集合を一致させる。

control.actionはstates_actionsのaction IDを参照する。hit.targetはaction.entrypointへ一致させる。同じ処理に複数の実入口がある場合、actionに任意の`entrypoints`配列を明記する（primary entrypointも含む）。各controlはそのいずれかを参照し、すべての宣言入口をcontrolで観測する。selectorの推測や処理IDの複製を必要としない。activation caseはstates_actionsのassertionで、targetをhit.target、`action`を同じaction ID、expectationを`{operator: equals, value: true}`とする。その領域への実入力が意図した処理を起動したことをproviderが取得する。単に44pxの無関係な外枠を測らない。操作のない画面はstates_actionsを理由付き非適用にし、controls=[]と非空のcontrols_reasonを記録する。

小さなタスク用ユーティリティは、本文に釣り合うnative印と、必要なら広げた操作可能なlabelから始める。例の20px印と44px領域はその用途の値であり、全製品の上限・強制wrapperではない。モバイル、少数タスク、タッチ領域の最低寸法だけでは見える印の拡大を正当化しない。明示的な弱視要件、既存の大きなコントロール体系、ユーザーの寸法指定は根拠として扱う。

copyの全itemに一意の`id`、roleとは独立した`purpose`、実出典への`source_ref`、削除・短文化した場合の影響を含む`alternative`、重複を残す理由`redundancy`を必須とする。purposeは`identity|data|action_label|state_guidance|error_guidance|explanation|encouragement|decoration`。statusやlabelというroleでも省略できない。通常の空・完了・エラー案内は、状態の事実と次の操作を必要に応じて示す。メッセージを求める一般的な要件だけでは励ましを許可しない。

encouragement/decorationはさらに`authorization_ref`を持つ。pathとpointer/anchorに加え`provenance: original_brief|baseline_specification`を指定する。既定のmode=exact_textでは参照の値を表示文と正確に一致させる。prepare以前にinputsへ原依頼を保存するか、baselineの定義元または確定したrequirementsに含めておく。snapshot.input_digests/source_digests/requirements_digestsのhashで固定し、現在の実装ファイル・input_globs内のbaselineアプリ定義元（CSS/JS等も含む）・Registry・実装後の根拠・広いREQ IDを許可文言の代わりにしない。承認済み定義元であっても許可テキストの変化は拒否する。原依頼が明示的に励まし・ブランドcopyの文章作成を委任している場合は、`mode: commissioned_copy`を選べる。provenanceはoriginal_briefとし、参照先は実装前に固定した非空の原指示文にする。`scope: {purpose, case_ids, description}`で対象purpose、当該itemのinventory case全件、具体的な用途の範囲を記録する。scopeと現設計のpurpose/case集合の不一致や空の範囲は拒否する。委任があれば生成した一文を別途再承認させる工程は作らない。

commissioned_copyというラベルだけで許可を証明したことにはならない。「空/全完了のメッセージ」など一般的な状態案内要求を、励まし文の作成委任へ読み替えない。独立レビューのsource_supported/purpose_appropriateで原指示の委任内容・範囲と実際の一文を確認し、根拠が足りなければrequest_changesとする。exact_textの文言一致と、両modeの凍結・実装元除外は維持する。原依頼を本当に引用したか、purposeを偽っていないかは独立レビューが判定する。機械は文章の意味や出典の真実性を推測しない。

`review.ui.expectation_assessments`は`measurements`、`controls`、`copy`の配列を持つ。各設計IDに一つずつ、全caseの正確な`case_ids`と非空の`evidence`・`rationale`を記録する。

| 対象 | 現設計への参照と合格に必要なboolean |
| --- | --- |
| measurements | `expectations: {case ID: 現在のexpectation}`、`bounds_appropriate: true` |
| controls | 四軸＋activationの`expectations`、`visual_appropriate: true`、`hit_appropriate: true`、`activation_associated: true` |
| copy | 現在の`text`、`purpose`、`source_ref`、`purpose_appropriate: true`、`source_supported: true`、`necessary: true`、`redundancy_justified: true` |

既存のreview fingerprintsとreceiptが設計・添付全体の鮮度を結び、assessmentは簡潔な値と判断を残す。原依頼と画面を先に確認し、小さい印＋同じ操作領域、状態事実＋短い文の代替を比較してから期待値へ照合する。不適切な範囲やcopyは実測が完全一致でもrequest_changes。欠落・否定的判断を空のexcess/missingで覆せない。これは判断の記録と欠落検出であり、レビュアーの誠実さ・意味理解の正しさの機械的証明ではない。
