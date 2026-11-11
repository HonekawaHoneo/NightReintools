---
name: quality-review
description: 共通開発基盤で、別コンテキストから要件・設計・実装・検証をレビューし、根拠のある指摘と判定を記録する。
---

# 独立レビュー

実装者とは別の人または新しいCodexセッションで実行する。
AGENTS、protocol、対象変更の成果物、関連コードとテスト、evidenceの実行結果を読む。
可能ならGit差分も読み、要件から実装・検証への対応を確認する。
構造検査が有効ならstructural-quality.mdに従い、structural_review全項目の根拠、baselineとの差、改名による循環再同定、既存負債と新規・拡大負債を確認する。依存図だけで意味的重複・凝集度を判断しない。未実施検査とobserveで残った違反を成功に読み替えない。

1. 全受入条件と、既存の挙動を保つ要件について、コードとテストが意味的に十分か確認する。
   protocol.mdの「原指示と目的の契約」に従い、goalの達成と元のrequest全体・確定要求・制約の充足を別々に評価する。request_itemsへの分解漏れ・誤分類も原文に戻って調べ、対応IDだけで合格にしない。例示の条件、指定手段、変更禁止範囲を保護する。
   intent_reviewへpurpose、全source、minimalityのstatusと具体的根拠を記録する。非確定の仮説・手段は採否の妥当性を照合する。より単純な既存解・責務と依存・過不足を確認し、構造レビューがある項目はその根拠を参照して重複分析しない。片側だけの達成や未検証はpassedにしない。
2. 設計の前提、影響範囲、回復手順と実装が合っているか確認する。
3. 実行証跡が現在コードに対応するかCLIのcheckで確認する。合格表示だけをコードの正しさの証明にしない。
4. 指摘には根拠と重要度を付ける。blocker・majorが残ればdecisionをrequest_changesにする。minorを受容する場合は理由をresolutionに記載する。
5. `python3 .harness/harness.py fingerprint <id>` のproject_digestとartifacts_digestをreview.jsonに記録する。
6. 別のreviewerとcontext、確認した全要件ID、総合判断、制約を記録する。判定を捏造しない。
7. passedの場合はadvanceを使う。修正が必要なら実装者へ具体的な指摘を返し、再検証後に再レビューする。

レビュー中にソースを直した場合は指紋が変わる。実装工程でrunを再実行し、修正後のコードを別コンテキストで確認する。
