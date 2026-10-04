---
feature_id: nightreign-boss-tool
document_id: NRT-DES-001
document_version: 0.11.3
document_set_version: 0.11.3
related_documents: NRT-REQ-001@0.11.3, NRT-SPEC-001@0.11.3, NRT-PLAN-001@0.11.3, NRT-MAP-001@0.11.3
code_revision: 74cdde38f096b2296d62ad0a0b278110dde0c81b
author: Codex
reviewer: Codex main (user-authorized); no designated specialist reviewer is configured
status: approved
---

# 設計

## 採用方式

GitHub Pagesのブランチ公開を使い、mainブランチのルートを公開元にする。アプリは既に静的ファイルとして構成され、独自ビルド処理を必要としないため、GitHub Actionsや追加の公開ブランチを導入しない。GitHub Pagesの標準Jekyll処理を使い、ルートの_config.ymlでアプリ以外の補助ファイルを生成サイトから除外する。

## 配信ファイル

配信対象はindex.html、styles.css、resistance.css、app.js、mapping-data.js、resistance-data.js、manifest.webmanifest、service-worker.js、assets内のアイコンとする。README、docs、LAN配信用PowerShell/バッチ、certificatesはJekyllのexcludeで除外する。生成されたLAN証明書フォルダーは.gitignoreでも無視する。

## PWAパス

既存HTML、Manifest、Service Workerは相対URLを使う。プロジェクトサイトのリポジトリパス配下でアプリを開けば、Manifestのscope/start_urlとService Workerの相対キャッシュパスはその配下で解決する。アプリのランタイムコードと既存キャッシュ名は変更しない。

## セキュリティ

Pagesは静的コンテンツのみを配信する。閲覧者から運用者PCへ接続するAPI、プロキシ、サーバー処理を追加しない。Service Workerは既存どおり同一オリジンのGETだけを扱い、外部オリジンの要求を横取りしない。公開サイトの更新はリポジトリ上のコード変更を通じて行う。アカウント保護やブランチ保護の設定は今回の変更範囲に含めない。

index.htmlのCSP metaポリシーは`default-src 'self'`とし、script/style/image/manifest/connect/workerを明示的に`'self'`に限定する。`base-uri 'none'`、`object-src 'none'`、`form-action 'none'`も指定する。既存HTMLは外部URLの実行資源とインラインスクリプト/スタイルを使わないため、この方針でPWA資源を読み込める。未認識の資源種別も既定で同一サイト内に限られる。Referrer Policyは`no-referrer`とする。CSPは同一サイトから配信された悪意ある変更を防ぐ仕組みではない。

Jekyllのexcludeは生成サイトにだけ適用される。リポジトリ自体は公開されるため、README、docs、LAN配信スクリプトなどのソースも閲覧可能である。証明書と秘密鍵は履歴を含むリポジトリに含めない。

## Pagesのアクセス制御根拠

対象は個人アカウント`HonekawaHoneo`の公開リポジトリである。GitHub公式仕様ではPagesサイトを限定公開するにはGitHub Enterprise Cloudの組織が所有するprivate/internal project repositoryが必要とされる。この個人リポジトリでは閲覧者を限定できないため、ユーザーの条件付き許可に基づき公開サイトとして準備する。参考: [Changing the visibility of your GitHub Pages site](https://docs.github.com/en/enterprise-cloud@latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site)。

## 依存と運用

新しいライブラリ、Action、外部API、ビルドランタイムを追加しない。GitHub Pages設定では **Deploy from a branch / main / /(root)** を選ぶ。Pagesの管理設定はリポジトリ管理権限を持つ利用者が行う。

## 一時検証ツールの監査と結果

監査日: 2026-10-03。候補ツールはローカル試験用に限り、リポジトリへ依存ファイルを追加しない。

| 構成要素 | 候補版・ライセンス | 結果 |
|---|---|---|
| RubyInstaller / Ruby | 3.3.12 / BSD-3-Clause。公式リリースは2026-07-21。配布ファイルのSHA-256と署名を確認。 | 一時領域のみへ導入。PATH追加、関連付け、MSYS2自動セットアップは無効にし、ユーザーPATHに変更がないことを確認。 |
| GitHub Pagesのローカル依存 | github-pages 232 / MIT、bundler-audit 0.9.3 / GPL-3.0-or-later、Nokogiri 1.19.4以上 / MIT。 | 一時Gemfileで導入を試したが、Windows/MSYS2上のnative extension構築で失敗。bundler-auditとJekyll実ビルドは未実行。 |
| MSYS2 UCRTビルドツール | binutils 2.47-3候補 / GPL-3.0-or-later。 | 公式情報にHighのCVE-2026-3442とCVE-2026-3441が掲載。インストール済みDevKitの推移依存の正確な版と脆弱性適用範囲を確認できず、最近の侵害・悪用状況も未確認。監査判定はHold。 |

一時インストールとキャッシュは削除済み。監査Holdのため、追加導入やビルドは行わない。参考: [RubyInstaller 3.3.12](https://github.com/oneclick/rubyinstaller2/releases/tag/RubyInstaller-3.3.12-1)、[github-pages 232](https://rubygems.org/gems/github-pages/versions/232)、[bundler-audit 0.9.3](https://rubygems.org/gems/bundler-audit/versions/0.9.3)、[Nokogiri GHSA-p67v-3w7g-wjg7](https://github.com/sparklemotion/nokogiri/security/advisories/GHSA-p67v-3w7g-wjg7)、[MSYS2 UCRT binutils](https://packages.msys2.org/packages/mingw-w64-ucrt-x86_64-binutils)。Nokogiriの当該Low advisoryは1.19.4で修正されている。
