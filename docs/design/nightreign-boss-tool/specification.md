---
feature_id: nightreign-boss-tool
document_id: NRT-SPEC-001
document_version: 0.11.3
document_set_version: 0.11.3
related_documents: NRT-REQ-001@0.11.3, NRT-DES-001@0.11.3, NRT-PLAN-001@0.11.3, NRT-MAP-001@0.11.3
code_revision: 74cdde38f096b2296d62ad0a0b278110dde0c81b
author: Codex
reviewer: Codex main (user-authorized); no designated specialist reviewer is configured
status: approved
---

# ユーザー向け仕様

## Webサイト

公開URLは https://honekawahoneo.github.io/NightReintools/ です。リポジトリ管理者がGitHub Pagesをmainブランチのルートから配信する設定を保存すると、HTTPSのサイトとして利用できます。iPadからGitHubへサインインする必要はありません。

## iPadでの利用

Safariで公開URLを開きます。共有メニューからホーム画面に追加します。「Webアプリとして開く」が表示された場合は有効にして追加します。最初の読み込み時に静的ファイルがキャッシュされると、オフラインでも起動できます。

## 公開範囲と動作

サイトとソースコードは公開されます。この個人リポジトリではサイト閲覧者を限定できません。アプリはブラウザー内で動き、選択内容や検索語はページ内メモリーだけで扱います。外部サービスへの送信やブラウザー保存領域への保存は行いません。アプリへのアクセスが利用者のWindows PCを通ることはありません。CSPによりアプリの資源と通信は同一サイトに限定されます。README、設計資料、Windows向けLAN配信スクリプトと証明書ディレクトリはPagesサイトから除外されますが、公開リポジトリでは閲覧できます。

## 変更状況

文書セット0.11.3ではindex.htmlに同一サイト限定のCSPとReferrer Policyを追加します。画面や選択操作に変更はありません。GitHub Pagesへの反映と公開は未完了です。
