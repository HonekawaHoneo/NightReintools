# Standard Implementation Path Verification

対象は新しいUI実現方式、実装方式の変更、Complexity Escalation Gate発火時。
既存方式で満たす小変更は既存決定への参照で足りる。

| 確認順 | 得るもの |
| --- | --- |
| 要求と制約 | 意味、操作、対応OS/ブラウザ、入力、配布・権限・性能、確定した受入条件 |
| 既存実装 | 部品、共通操作、フレームワーク機能、既存UIライブラリと版 |
| 標準経路 | browser/OS標準API、実績あるライブラリ、一般パターンと一次資料 |
| 適合性 | host bridge、thread、sandbox、対応版、アクセシビリティ等の実際の制約 |
| 最小検証 | 不確実な接続だけの入力・実行環境・観測・未確認事項 |
| 決定 | 採用理由、標準方式が満たせない条件、必要な複雑さと見直す条件 |

既存・標準経路で充足する根拠を得たら調査を終えてよい。
他アプリの実績は候補発見の根拠であり、別の技術・権限でも簡単だという証明ではない。

## Complexity Escalation Gate

標準機能の独自再実装、補正処理の増加、同じ問題の再発、過剰な状態同期、
無関係な部品への変更波及を検出したら`investigate`とする。
当該方式への補正追加と完了宣言を止め、要求・再現・根本原因・標準API・比較条件を確認する。
不具合の再現・原因分析・仮説検証には利用可能なsystematic-debugging等を使い、別工程を作らない。

方式を修正して受入を満たせば`clear`、必要な複雑さと実行証拠を説明できれば`justified`。
未解決を名前だけ変更して通さない。重要境界・要求・権限を変える場合は現在の許可範囲を確認する。
段階1は手続きとレビューによる停止であり、harness.pyがこの状態を自動検査するわけではない。

## Windows右クリックの分岐

次を要求から区別する。

1. Web内の独自メニュー。
2. WebViewの既定メニュー編集。
3. アプリからShellオブジェクトのネイティブメニューを表示し、独自項目を統合。
4. Explorer側のメニューへ項目を登録。

3の調査候補は`IShellFolder::GetUIObjectOf`から`IContextMenu`を取得し、
`QueryContextMenu`と`InvokeCommand`で構築・実行する標準経路。
対象技術の既存bridge、対応OS、所有window、COM/thread、コマンドID、
必要に応じたIContextMenu2/3へのメッセージ転送と解放を照合する。
これをそのまま全フレームワークで使える実装と断定しない。

4は静的verb・handler等の別経路を調査する。
WebView2のContextMenuRequestedはWebViewメニューの編集であり、Shellメニュー取得と同一視しない。

単一/複数選択、対象ファイル/フォルダ、独自項目、native項目、取消、キーボード、
DPI、Shell拡張の必要範囲をWindows上で確認する。
Webモックの成功は入口・文脈・独自項目のUI案に限定し、Windows検証はblockedのまま残す。

一次資料：

- [IContextMenu](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-icontextmenu)
- [Shortcut Menu Handlers](https://learn.microsoft.com/en-us/windows/win32/shell/context-menu-handlers)
- [WebView2 ContextMenuRequested](https://learn.microsoft.com/en-us/microsoft-edge/webview2/reference/win32/icorewebview2contextmenurequestedeventargs)
