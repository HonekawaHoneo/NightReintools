---
feature_id: nightreign-boss-tool
document_id: NRT-PLAN-001
document_version: 0.11.3
document_set_version: 0.11.3
related_documents: NRT-REQ-001@0.11.3, NRT-DES-001@0.11.3, NRT-SPEC-001@0.11.3, NRT-MAP-001@0.11.3
code_revision: 74cdde38f096b2296d62ad0a0b278110dde0c81b
author: Codex
reviewer: Codex main (user-authorized); no designated specialist reviewer is configured
status: in-progress
---

# 実装計画とゲート記録

## 作業単位

- Feature ID: nightreign-boss-tool
- Feature version: 0.11.0; document-set version: 0.11.3
- 許可範囲: 既存の0.10.2 PWAをGitHub Pagesで公開し、main / root公開元、不要ファイルの除外、CSPとReferrer Policy、README手順、5文書とmanifestを更新する。閲覧制限が使えない場合は公開するというユーザー許可を確認した。
- 既存プロジェクトの棚卸し: 公開GitHubリポジトリは空。ユーザー提供のPWA ZIP（0.10.2、22ファイル）を初期ベースとしてmainに取り込んだ。PWA実行ファイル、LAN起動スクリプト、README、設計文書の内容を確認した。ユーザーはmain初期化と指定ブランチ階層を承認した。2026-10-03に、専門レビュアー未設定のためメインエージェントが検証とレビューを担当することが承認された。
- 類似機能探索: 既存README、feature文書、Manifest、Service Worker、LAN HTTPS配信スクリプトを確認した。Pages向け設定は存在しない。既存Service Workerは同一オリジンだけを扱い、外部APIやバックエンドはない。
- 依存: リポジトリには追加なし。GitHub Pagesの標準ブランチ公開/Jekyll除外設定を使用する。一時検証ツールの監査結果はdesign.mdに記録。
- 公開設定: Settings > Pages > Deploy from a branch > main > /(root)。管理権限による保存が必要。個人アカウント配下の本リポジトリは限定公開できず、サイトとリポジトリの内容がインターネットから見える。
- ブランチ: main > release/0.11.0 > work/nightreign-boss-tool-pages > codex/nightreign-boss-tool-pages-pages-setup。
- 影響: Pages公開をmainに設定するとサイトとリポジトリの全ファイル・履歴がインターネットから見える。README/docs/LANスクリプトをPagesから除外してもGitHubのソース表示からは除外されない。証明書と秘密鍵は含めない。公開サイトにはPWA実行ファイルのみを含める。

## 実装順と進捗

1. 完了: mainへ既存PWA 0.10.2を初期ベースとして追加し、ローカル初期コミットを作成。
2. 完了: featureブランチ上で_config.ymlと.gitignoreを追加し、公開対象をPWAファイルに限定。
3. 完了: READMEと機能文書をfeature 0.11.0 / document set 0.11.3へ同期。
4. 完了: 公開前の秘密情報監査で、reachable Git履歴と作業ファイルに秘密鍵、証明書、GitHubトークンなどの検出なし。履歴はPWA初期ベースの1コミットで、certificatesディレクトリも存在しない。アプリの外部API/送信/永続保存/HTML文字列sinkも検出なし。
5. 完了: index.htmlに同一サイト限定のCSPとReferrer Policyを追加。外部コード、外部通信、インライン実行を許可しない。
6. 完了: Node静的検査でCSP、Referrer Policy、HTML相対参照、JavaScript構文、危険なDOM sink/永続保存APIの不在、Service Workerの同一オリジン制約、Jekyll/Git除外、文書版整合を確認。index.htmlからCSP/Referrer Policyの2行を除くとHEADと一致し、他のPWA資源も変更なし。`git diff --check`通過。Windows Chromeで`127.0.0.1`の`/Nightreintools/`プレビューを開き、画面とボス選択・結果描画を確認。GitHub Pages/Jekyll実ビルドとは別の検査。
7. 公開後確認: GitHub Pages/JekyllはGitHub側でビルドされるため、ローカルにLinux/Ruby/Jekyllを導入しない。公開元をmain / rootに設定した後、Pagesのビルド実行結果、公開URL、PWA相対資源とService Workerを確認する。失敗時は公開後レビューからCorrection/Retest/Re-reviewを行い、成功するまで完了としない。GitHubリモートはOpenSSL TLS経由の読み取りに成功し、現時点で空。
8. 保留: iPad Safari実機での初回起動とホーム画面追加確認。

### 0.11.3 公開先コミット参照の同期

- 5文書とmanifestを文書セット0.11.3へ同期し、code_revisionをGitHub作業ブランチ上のPWA実装コミット 74cdde38f096b2296d62ad0a0b278110dde0c81b に合わせた。機能バージョン0.11.0と実行時の挙動は変更しない。
- Retest: manifest JSON、5文書の版・相互参照・code_revision一致、差分空白を確認。
- Re-review: 文書メタデータと作業ブランチのリモートコードコミットの参照整合を確認。

## ゲート

| Gate | 状態 | 根拠 |
|---|---|---|
| Requirements | Pass | GitHub Pages利用、公開、iPad Safari利用、静的配信、Windows PCを中継しない条件を確定。 |
| Design | Pass | ビルド不要のブランチ公開とJekyll除外を採用。追加Actionや依存を避ける。 |
| Pre-implementation review | Pass | 既存ランタイム・相対パス・Service Worker・LANスクリプトを検索。配信対象と除外を特定。 |
| Implementation | Pass | Pages設定、README、CSP/Referrer Policy、文書セット0.11.3を準備。PWA判定ロジックや画面表示は変更していない。 |
| Test | Pass | 静的検査、Windows Chromeでのサブパス表示/ボス選択、秘密情報監査、`git diff --check`がPass。実GitHub Pagesビルドは公開後確認として別記録する。 |
| Post-implementation review | Pass | 配信元/除外範囲、CSP、同一オリジンService Worker、外部送信と保存の不在、公開リポジトリに見える全ファイルを確認。重大な未対応所見なし。 |
| Correction | Pass | ローカルレビューで追加修正なし。GitHub側ビルドで問題が出た場合は別途修正する。 |
| Retest | Pass | CSP最終値に対してNode静的検査とWindows Chromeの表示/選択を再実施。 |
| Re-review | Pass | 最終ローカル差分と5文書/manifestの0.11.3整合を再確認。公開後のPages動作確認はまだ完了していない。 |

## 復旧

Pages設定を解除するか、mainのPages設定を別の公開元へ戻すとPages配信を止められる。公開リポジトリへpush済みのコードはGitHub履歴から閲覧可能なままなので、秘密情報を誤って含めた場合は履歴削除と関連資格情報の失効が別途必要。アプリ判定ロジックと画面は0.10.2のままにする。
