---
feature_id: nightreign-boss-tool
document_id: NRT-MAP-001
document_version: 0.11.3
document_set_version: 0.11.3
related_documents: NRT-REQ-001@0.11.3, NRT-DES-001@0.11.3, NRT-SPEC-001@0.11.3, NRT-PLAN-001@0.11.3
code_revision: 74cdde38f096b2296d62ad0a0b278110dde0c81b
author: Codex
reviewer: Codex main (user-authorized); no designated specialist reviewer is configured
status: in-progress
---

# コードマップ

## ファイルと責務

| ファイル | 責務 |
|---|---|
| index.html | アプリ見出し、出撃情報、ステージ結果、夜の王候補の意味構造。CSS、スクリプト、Manifest、アイコンを相対パスで読み込み、CSPとReferrer Policyを宣言する |
| styles.css | アプリ外枠、カテゴリ見出し、選択欄、結果カテゴリ、全体レイアウト |
| resistance.css | 属性/値の表、候補要約、種類/効果色、ボス名行と展開表の階層、レスポンシブ表示 |
| app.js | クロージャー内の選択状態、検索、候補集合交差、表DOM生成、開閉領域の描画 |
| mapping-data.js | 夜の王・遭遇・イベント候補の対応表 |
| resistance-data.js | 物理/属性補正、状態異常蓄積値と表示名 |
| service-worker.js | 登録スコープ配下の静的ファイルをキャッシュし、同一オリジンのGETだけを扱う |
| manifest.webmanifest | PWA名、表示形式、色、相対起動先、アイコン |
| assets/icon.svg, assets/icon-180.png, assets/icon-192.png, assets/icon-512.png | ブラウザーとホーム画面用のPWAアイコン |
| _config.yml | GitHub Pages/Jekyllの公開対象を制限。README、docs、証明書、LAN起動スクリプトを除外 |
| .gitignore | ローカル生成証明書とJekyll出力をGit管理から除外 |
| README.md | アプリの使い方、Pages公開元の設定、iPad利用、公開範囲とセキュリティ境界、データ出典 |
| start-https.bat | Windows LAN HTTPS起動ラッパー。Pages対象外 |
| start-https.ps1 | LAN IPv4選択、ローカル証明書生成、公開証明書出力。Pages対象外 |
| https-static-server.ps1 | LAN IPv4への限定HTTPS静的配信。Pages対象外 |
| certificates/* | 起動時に作られる公開証明書。GitとPages対象外 |
| docs/design/nightreign-boss-tool/* | この機能の要件、設計、仕様、計画、コードマップ、manifest。Pages対象外 |

## 実行経路

1. GitHub Pagesがmainのルートをビルド元として静的サイトを作る。
2. _config.ymlがPWA実行に不要なREADME、docs、LANサーバー関連ファイル、証明書ディレクトリを除外する。
3. index.htmlがデータ、CSS、app.js、Manifest、アイコンを相対パスで読み込む。
4. service-worker.jsが既存のGET要求を同一オリジンに限定してキャッシュする。
5. iPad SafariはGitHub PagesのHTTPS URLを開き、ホーム画面追加後はブラウザー内でアプリを実行する。利用者PC上で配信プロセスは動かない。
6. 同梱LAN配信を使う場合は、`start-https.bat` が `start-https.ps1` を起動し、選択したプライベートIPv4とHTTPS URLを表示する。
7. `start-https.ps1` は現在のユーザー証明書ストアにCA秘密鍵とIP SAN付きサーバー証明書を作り、iPadへ送る公開 `.cer` のみを書き出す。
8. `https-static-server.ps1` は選択IPv4の8443番ポートに限定して待ち受け、許可リストにあるPWAファイルだけを返す。LAN配信のREADME、スクリプト、証明書、docsは許可リストに含まれない。

## UIのデータフロー

1. `index.html` の各検索inputが `app.js` の検索状態に紐付く。
2. 1日目、2日目、イベントのbuttonが単一の選択状態を更新する。1日目変更時は2日目を解除する。
3. `getCandidates` が選択項目の候補集合を交差し、成立する組み合わせにだけナメレス特殊条件を追加する。`noBoss` の2日目項目も1日目の特例IDを確認する。
4. `getDay1Options`、`getDay2Options`、`getEventOptions` が残り2つの選択を反映する。通常ボス候補はナメレスを除く夜の王が残る項目だけを表示し、ナメレス専用の「該当なし」は成立時に残す。
5. `renderCandidates` が候補ごとのdetailsと簡易表を生成する。実候補一覧にはナメレスも含める。
6. `renderSelectedResistances` が日程別遭遇個体をdetailsに分ける。
7. `createBossDetails` が候補、遭遇個体、形態の開閉領域を作る。
8. `addResistanceTable` が種類名と数値を2列のtableにする。`createQuickResistanceSummary` は物理・属性・状態異常の3表を並べ、標準値がない群も見出し位置を保つ。
9. `service-worker.js` の0.9.1 cacheがHTML、CSS、JS、データ、manifest、アイコンを保存する。

## 関数・データ境界

- `getDay1Options`、`getDay2Options`、`getEventOptions`: 他2選択に整合する入力候補。
- `getCandidates`、`intersect`、`isNameresPossible`: 判定ルールとナメレス特殊条件。`noBoss` は有効な特例対象だけに制限。
- `renderOptions`、`showSelected`、`updateSelectionLists`: 入力コントロール表示。
- `addResistanceTable`、`createQuickResistanceSummary`: 詳細表と候補用3列省標準値表。
- `appendRecordContent`、`createBossDetails`: 個体/形態単位の開閉と完全表。
- `renderCandidates`、`renderEncounterResistances`、`renderSelectedResistances`: ステージ結果の描画。
- `select`、`bindSearch`、`render`: UI状態とイベントの入口。
- `mapping-data.js` と `resistance-data.js` はデータ定義を所有し、`app.js` がそれを読む。Pages対応はルート設定とREADME、設計文書で行い、アプリ機能コードへ新しい依存や状態を導入しない。

## 環境・依存・変更影響

実行時依存なし。新しい外部パッケージ、Action、API、DB、計測機能を追加しない。GitHub Pages標準のブランチ公開を使う。index.htmlのCSP/Referrer Policy以外は0.10.2の既存PWA資源を変更しない。判定ロジック、画面、CSS、JavaScript、データ、Manifest、Service Worker、アイコンは同一に保つ。自動テストやfixtureはリポジトリに含まれず、検証結果と未実施項目はplan.mdに記録する。

## 0.11.3での影響

index.htmlが同一サイト限定のCSPとReferrer Policyを設定する。画面、判定、保存方法、実行依存は変更しない。Jekyll実ビルドと公開後確認の状態はplan.mdに記録する。
