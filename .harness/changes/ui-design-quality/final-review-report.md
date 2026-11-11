# UI最終独立レビュー

判定は `passed`。未解決の blocker、major、minor はありません。

原依頼と実画像・実操作を先に確認し、設計の期待値と照合しました。候補結果が結果領域の先頭に移り、選択・無効・展開と数値の意味を読み取れます。既存の判定とデータは維持しています。

レビュアーは `ui-final-independent-reviewer`、コンテキストは `/root/ui_review_final` です。`ponytail-review`、`quality-review`、`semantic-ui-design`、`ui-implementation-harness` を適用しました。文書は `unslop` と `technical-writing`、完了前照合は `verification-before-completion` に従います。

## 解消した指摘

- R1。開いた使い方、全表、形態、2日目とイベントの選択、検索不一致を代表シナリオへ追加しました。input の値と placeholder も取得します。既存5シナリオを含む8状態の全文を確認しました。
- R2。静的な見出し、属性、所属の印を操作名から分けました。出典は実HTML、描画関数、ゲーム定義、計画時の定義と固定fixtureを指します。
- F1。最終レビューで残っていた「イベント」見出し4 IDと「1日目を先に選択」1 IDの分類を指摘しました。前者は `identity`、後者は `state_guidance` へ修正されています。実DOMの h3 と disabled input に戻って理由も確認しました。製品・テスト・fixtureの変更はありません。

## 確認した結果

- 全10原則、5 measurement ID、8 control ID、533 copy IDに、現在の期待値・実出典・必要性・代替・重複の判断を記録しました。全表示文は8状態で57、151、151、151、151、217、217、108件です。スクロールする選択肢とfocus時のskip linkも含む取得範囲です。
- 実画面は1440、1024、390pxと320px相当のCSS拡大で確認しました。独立した実操作21件では、選択、候補3体から2体への絞り込み、検索不一致、alias、解除、reset、候補と形態とhelpの開閉、320、390、768、1024pxを確認しました。JavaScriptエラーはありません。
- 選択印は12pxで、実操作域はdesktop167×52px、mobile161×52pxです。見出しは24px、選択肢の行高20px、代表行高44または52px、reset44px、領域間20pxです。小さい印と同じ操作面で目的を満たし、大きい印は不要と判断しました。
- 新しい不変receiptで216ケースが成功しています。内訳は208 assertion と8 visual observationです。18遭遇の基準比較、検索と解除とreset、event-only、320と768px、実際の旧cache0.9.1から0.9.2への更新とoffline起動も成功しています。現在のreceiptの添付33件をSHA256で照合しました。
- `app.js`、`mapping-data.js`、`resistance-data.js` はbase `2e39352` とbyte-for-byte一致します。製品の変更はHTML、2つのCSS、Manifestの色、Service Workerのcache名です。CSPと相対パスを保持し、runtime依存・外部通信・backendを追加していません。
- 環境lockの380ファイルと6 skillファイル、対象lockの361ファイルを独立に照合し、全一致しました。配布元は `1f95e672c6225047709eb47dbb5e710ad7a5e240`、VERSIONは0.9.0です。framework試験ログは300件成功、38件任意skipです。
- 負例receipt `246878e84b354305bc49adaf075e953f` は、試験DOMの42px見出しと追加本文によって24ケースを拒否しています。ソースは不変で、比較条件の問題は0件です。これは検出機構の確認であり、意味の妥当性は本レビューが別に判断しています。

## レビュー対象

- 不変receiptは [`evidence/090f6b3ba9524fd3a7583090b1d0b6ab.json`](evidence/090f6b3ba9524fd3a7583090b1d0b6ab.json)。SHA256は `088d0aff9b79a2112a04a6372e2db97112db7021868af6472cbfcbb9d59803c0`。
- `project_digest` は `125eb452cd0678dc63ca9a7aa3dd4a34399b28474f0bb6b3319ad2979db31b98`。
- `artifacts_digest` は `2e29afa23b128401d85308d9a5c325e21bb1524cda851b9982a422b35d633a58`。
- レビュー時のHEADは `999e53818eee3c82ac86a2fcfbf5aa77d109ec8e`。全IDの詳細は [review.json](review.json) にあります。

`python3 .harness/harness.py check ui-design-quality` はexit 0、`phase=review`、`valid=true`でした。続けて取得した両指紋も上記と一致しました。`advance` は実行していません。

## 未確認の範囲

SafariとiPadの実機、ブラウザー本体のzoom、WCAG全面適合は未検証です。CSS zoomはレイアウトの代替試験です。既存の選択肢DOM再生成後のfocus保持を改善済みとはしていません。環境Publishと新規チャットの自動読込も未実施です。任意の構造・累積品質検査は未設定です。

レビュアーは製品・テスト・設計・工程状態を変更していません。工程移行、commit、pushは親担当が行います。今回の保存対象は `review.json` と本報告だけです。
