# UI実装から検証への接続

設計の正本はdesign.ui。要件・meaning・scenario・case IDを引き継ぎ、別文書で期待値を変えない。詳細な形式は`.harness/ui-principles.md`を参照する。

1. 実装前に10原則とcaseを確認する。操作入口、状態所有者、更新する表示、実処理接続、関連利用先を特定する。新規UIはui schema_version=3（既存v1/v2は明示移行時のみ）・enforceと実行可能なcheckを登録してからnewを実行する。
2. 実装では既存部品と実トークンを参照し、表示文・文字サイズ・余白を設計から増やす場合は先に設計へ戻る。検証を通すために期待値を現物へ合わせない。
3. 各操作について成功・失敗・取消・重複・遅延応答・フォーカスを調べる。ローカル同期処理で遅延が存在しない等は理由付き非適用にする。適用される結果は実操作と可視結果をassertion caseで確かめる。文字の進捗と視覚表示、保存状態と再読込結果も一致させる。
4. Browser/Playwright等の既存手段で寸法、全表示文、状態、操作結果を取得する。CSS宣言値だけでなくcomputed styleやbounding boxを測る。全表示文の対象を狭めて余分なコピーを除外しない。
5. providerはscenarioごとのスクリーンショットとmetrics/aria/traceを保存し、case_resultsのvalue_refで実測箇所を指す。ハーネスが期待値と比較する。返却statusだけで合否を作らない。
6. 幅・拡大・キーボード・フォーカス・ラベル・読み順・対象寸法を確認する。各接続がmock/partial/unimplemented/productionのどれかと、実際に確かめた範囲を残す。
7. 独立レビュアーに特定のreceipt、画面、操作証跡、設計を渡す。10原則すべての観測・過剰・不足を記録する。コードや証跡を直したらrunとレビューを更新する。

検証設定の削除、v1への変更、enforceの解除で工程を通さない。接続がない、観測できない、適用すべき結果が未実装なら未完了として残す。静的モックやブラウザ内の代用品を本番接続の成功と記録しない。

v3はcontrolsのvisual/hit幅・高さと、hit領域への入力によるactionの実起動を同じscenarioで取得する。visible glyphを44pxの操作領域に合わせて拡大しない。全copyのid/purpose/source_ref/alternative/redundancyを引き継ぎ、encouragement/decorationは文言指定のexact_textと、原依頼による明示的な制作委任のcommissioned_copyを区別する。後者は原指示とpurpose・inventory case全件・用途の範囲をprepare前に固定し、生成文の再承認を求めない。一般的な状態メッセージ要求は制作委任の代わりにならない。review.ui.expectation_assessmentsでは寸法上限、視覚的妥当性と起動関連、copyの目的・根拠・必要性・重複を各IDで判断する。期待値が不適切なら実測一致でも通さない。
