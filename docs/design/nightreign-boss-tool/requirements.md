---
feature_id: nightreign-boss-tool
document_id: NRT-REQ-001
document_version: 0.11.3
document_set_version: 0.11.3
related_documents: NRT-DES-001@0.11.3, NRT-SPEC-001@0.11.3, NRT-PLAN-001@0.11.3, NRT-MAP-001@0.11.3
code_revision: 74cdde38f096b2296d62ad0a0b278110dde0c81b
author: Codex
reviewer: Codex main (user-authorized); no designated specialist reviewer is configured
status: approved
---

# 要件

## 目的

既存の夜の王チェッカーをGitHub PagesでHTTPS公開し、iPadのSafariから利用できるようにする。配信は静的ファイルに限り、閲覧者の通信が利用者のWindows PCを経由する構成を作らない。

## 今回の変更範囲

- 既存PWAの画面、データ、操作、CSS、JavaScript、Manifest、Service Workerを維持し、index.htmlに同一サイト限定のContent Security PolicyとReferrer Policyを追加する。
- GitHub Pagesのブランチ公開を使い、mainブランチのルートをサイトとして配信する。
- Pages生成設定で、README、設計資料、Windows向けLAN HTTPSスクリプト、証明書ディレクトリを公開サイトから除外する。
- GitHub Pagesの設定手順とiPadでの利用方法をREADMEに記載する。
- 要件、設計、仕様、計画、コードマップ、manifestを文書セット0.11.3で同期する（機能バージョンは0.11.0）。

## セキュリティ境界

- GitHub Pagesとリポジトリはインターネット上で公開される。
- Webアプリはブラウザー内で動く静的PWAとし、サーバー、API、認証、DB、解析計測を追加しない。
- サイト訪問者の通信をWindows PCや家庭内LANへ中継する機能を追加しない。
- アプリの通信は同一オリジン上の静的PWAファイルに限る。選択内容を外部サービスへ送信しない。
- 秘密情報、証明書、秘密鍵をリポジトリやPages配信物に含めない。生成済み証明書ディレクトリはGitとPagesの両方から除外する。
- Pagesサイトに配信される変更は、mainへ反映された公開コードに基づく。リポジトリのアカウント保護は運用者が行う。
- Content Security Policyは外部スクリプト、スタイル、画像、通信、Manifest、Workerを許可しない。HTML、CSS、JavaScript、データ、画像は同一サイトから読み込む。
- 選択内容と検索語はページ内メモリーだけで扱い、ブラウザー保存領域や外部サービスへ送らない。

## 受け入れ条件

- Pagesのブランチ公開元をmain / rootに設定できる。
- 公開サイトのルートにindex.htmlがあり、CSS、JavaScript、データ、Manifest、アイコンを相対パスで読み込める。
- Service WorkerがPagesのプロジェクトURL配下で登録され、既存の同一オリジン静的ファイルをキャッシュする。
- 判定ロジック、画面構造、CSS、JavaScript、データ、Manifest、Service Workerは変更せず、index.htmlにはCSP/Referrer Policyのmeta要素だけを追加する。
- README、docs、start-https.bat、start-https.ps1、https-static-server.ps1、certificatesは生成サイトに含まれない。
- Pages向けにActions、外部ライブラリ、API、バックエンドを追加しない。
- CSPの許可先が既存PWAの同一サイト資源で足り、インラインスクリプト/スタイルが不要である。
- Pages除外設定は生成サイトだけを対象とし、公開リポジトリ内のファイルは閲覧可能であることをREADMEに明記する。
- READMEにPagesの公開設定、iPadでSafariから開く手順、ホーム画面追加、公開範囲とセキュリティ境界を記載する。
