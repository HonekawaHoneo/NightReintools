# UI検証

Python 3.10以上、Python Playwright、Chromiumを使います。アプリのランタイム依存はありません。このクラウド環境には両方が導入済みです。

```sh
python3 tests/regression.py
python3 .harness/harness.py run ui-design-quality
```

`regression.py`は、変更前に実ブラウザーから保存した18種の選択結果と照合し、検索・選択解除・リセット・耐性展開を確認します。判定ロジックとデータは固定SHA256と照合します。旧Service Workerと旧画面をHTTPサーバーから配信してから更新し、実際のキャッシュ移行とオフライン起動も確認します。

`ui_browser.py`は5シナリオの画面・全文・computed style・領域寸法・実操作結果を出力します。期待値の比較はCodexEnvSetが行います。画像と測定ファイルは変更単位の実行別証跡へ保存します。320px幅・768px幅の追加試験も行います。200%のCSS zoomはレイアウトの代替試験であり、Safari実機やWCAG全面適合を検証したものではありません。

検出を確認する場合だけ、`NIGHTREIGN_UI_PROBE=negative`を指定すると、試験中のDOMへ42pxの見出しと余分な文字列を入れます。ソースや期待値を変更せず、UIゲートが拒否することを確かめます。
