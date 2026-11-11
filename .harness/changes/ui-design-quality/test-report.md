# NightReintools UI品質チェック

CodexEnvSet main `1f95e672c6225047709eb47dbb5e710ad7a5e240`、バージョン0.9.0を現在のクラウド環境とNightReintoolsへ導入しました。NightReintoolsの基準はmain `2e39352`です。共通工程の変更IDは`ui-design-quality`です。

## アプリと変更

夜の王候補とボス耐性を確認する静的PWAです。1日目のボス、2日目のボス、イベントを選択すると候補を絞り込みます。

画面を暗い紺色へ整え、夜の王候補を結果欄の先頭へ移しました。選択・無効・フォーカスの区別、必要な空状態、使い方、数値の凡例を用意しました。候補の簡易耐性は狭幅でも表示します。余分なキャッチコピーや外部画像は追加していません。

製品の変更はindex.html、styles.css、resistance.css、manifest.webmanifest、Service Workerのキャッシュ名だけです。app.js、mapping-data.js、resistance-data.jsは基準SHA256と同一です。CSP、外部通信の範囲、判定ロジックは変更していません。ハーネス・UI定義・試験と工程証跡は、別途リポジトリへ導入しています。

## 検証

- ハーネス本体は338試験中300件が成功し、追加ツールを使う任意の38件をスキップしました。ログは[evidence/framework-tests.log](evidence/framework-tests.log)です。
- 環境の380管理ファイルと6スキルファイルを固定ロックへ照合しました。対象の初期化を再実行し、既存設定を保持したunchangedを確認しました。
- UI schema3、enforceを変更開始前に固定しました。10原則、5寸法、8種類の操作入口、全文inventoryを設計へ結びました。
- 実Chromiumの8シナリオで216 caseを観測しました。208 assertionが成功し、8 visual caseは画面レビューの対象です。正常実行のreceiptは[evidence/c27e5c9138b145cc89adba475abf7bca.json](evidence/c27e5c9138b145cc89adba475abf7bca.json)です。
- 18種類の1日目ボスから2日目候補・イベントへ進む結果を変更前と比較しました。別名検索、不一致、選択解除、リセット、耐性展開も成功しました。
- 320、390、768、1024、1440pxで収まりと操作領域を確認しました。640pxで200% CSS zoomのレイアウトも確認しました。
- 旧Service Worker 0.9.1と旧画面から、0.9.2の画面とキャッシュへ更新しました。その後、オフラインで起動してイベントから候補を選べました。
- 見出しを試験中のDOMだけで42pxへ変え、未要求の表示文を追加すると、24 caseが失敗してenforceが拒否しました。実装ソースと期待値は変更していません。[negative-probe-v2.json](negative-probe-v2.json)を参照してください。

初回の試験では、撮影条件にアプリ配色と補助zoom試験の説明を混在させたため、ハーネスが比較条件の不一致を検出しました。designへreopenし、元のUIファイルへ一時的に戻してbefore条件を再固定しました。画像自体は変更していません。ブラウザーの明色指定は共通の撮影条件であり、アプリの配色変更とは区別しています。[比較条件の実測](evidence/comparison-preference.json)を保存しました。

実測例として、デスクトップの見出しは24 CSS px、選択行は52px、選択印は12px、リセットの高さは44pxです。期待値と実寸の一致だけでは、寸法や文言の必要性を合格にしません。

## 画面

- [変更前のデスクトップ](evidence/before/desktop-selected.png)
- [変更後のデスクトップ](evidence/c27e5c9138b145cc89adba475abf7bca/ui-browser/desktop-selected.png)
- [変更後のスマートフォン](evidence/c27e5c9138b145cc89adba475abf7bca/ui-browser/mobile-selected.png)
- [変更後のタブレット](evidence/c27e5c9138b145cc89adba475abf7bca/ui-browser/tablet-selected.png)

## 確認範囲

独立レビューの結果はreview.jsonへ記録します。SafariやiPad実機、WCAG全面適合は検証していません。200% CSS zoomはレイアウトの代替試験です。

既存app.jsは選択時にボタンDOMを再生成します。試験は現在の入口でキーボード選択と解除を行います。再生成前のボタンにフォーカスが保持されるとは主張しません。

現在のクラウド環境への配置と、実際にファイルを読んで工程を実行するところまで確認しました。環境の保存・Publishや、新規チャットでのホストによる自動読込は別の操作であり、未実施です。個人プロファイルは標準のreview完了を使い、PR作成・mainへのマージ・本番公開は実行しません。

## 独立レビューへの対応

初回レビューでは、開いた使い方・検索不一致・全耐性表・形態・日別選択と入力placeholderの全文観測不足、および静的表示をaction_labelとした誤分類を指摘しました。元の画面を基準に3つの代表状態を追加し、入力値も観測へ含めました。静的な所属や属性名はidentityへ修正し、実装・元データ・描画関数へのsource_refを確認しました。旧レビューは[review-round1.json](review-round1.json)へ保存しています。最終判定は新しいコンテキストのreview.jsonへ記録します。
