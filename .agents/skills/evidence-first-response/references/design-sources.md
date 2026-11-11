# 設計根拠・由来・利用条件

更新日: 2026-11-10。v1.1.0を基に、本文の重複を整理し、依頼別の確認を別資料へ分離した。日本語優先、独立した判断、必要な根拠の確認、完了確認という既存原則を維持する。性能向上の主張は、別添の比較評価で実際に確認できた範囲に限定する。

## 今回参照した方法

| 資料 | 参照した点 | ライセンス |
|---|---|---|
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | 旧版との比較、出力を伏せた評価、結果と利用者のフィードバックによる反復 | [対象スキルのApache-2.0](https://github.com/anthropics/skills/blob/main/skills/skill-creator/LICENSE.txt) |
| [Superpowers writing-skills](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md) | 変更前の挙動を確認し、観測した失敗に対応する最小の変更を行う | [MIT](https://github.com/obra/superpowers/blob/main/LICENSE) |
| [Context Engineering advanced-evaluation](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/skills/advanced-evaluation/SKILL.md) | 判断基準の具体化、表示順を入れ替えた比較、長さや自信による評価の偏りへの対処 | [MIT](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/blob/main/LICENSE) |
| [OpenAI: Testing Agent Skills Systematically with Evals](https://developers.openai.com/blog/eval-skills) | 成功条件、実行結果、形式と効率を区別した評価 | 文書は参照のみ |
| [Anthropic: Demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | 機械判定・モデル評価・人による確認の使い分け。実際の状態を確認 | 文書は参照のみ |

他者のスキル本文・コードをこの改訂版へ転載していない。手法を参考に、日本語の本文と評価補助スクリプトを本用途に記述した。公開物の対象ライセンス本文は2026-11-10に確認し、取得した本文とファイル識別子は別添の評価資料に保存した。

上記MIT/Apache-2.0の公開物は、条件を守ることで業務用AIへの導入・改変・利用が可能。複製する場合、MITは著作権表示と許諾文を保持する。Apache-2.0は再配布時のライセンス添付・変更表示・該当する表示/NOTICE保持を確認する。対象外のファイル、依存物、AIサービス契約まで同じ条件とみなさない。本改訂はユーザーの既存スキルに新しい利用制限やライセンスを設定しない。通常の成果物生成だけで、これらのライセンスによる公開義務が自動的に発生するわけではない。元の素材を成果物に転載する場合は、その素材の条件を別に確認する。

## 旧版から継承した設計の由来

旧版の設計資料に記録されていた参照先。今回、これらを性能改善の実測根拠としては使わない。

- [Agent Skills仕様](https://agentskills.io/specification): SKILL.md、name、description、補助資料の構成。
- [英国AISI Ask don't tell](https://www.aisi.gov.uk/research/ask-dont-tell-reducing-sycophancy-in-large-language-models): ユーザーの断定を中立な検証質問として扱う原則。
- [OpenAI Model Spec](https://model-spec.openai.com/2025-09-12.html): 独立した判断、ユーザー主体性、根拠と確認範囲の区別。
- [Superpowers verification-before-completion](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md): 確認できる証拠なしに成功・完了を主張しない原則。

## 導入・動作確認の境界

このスキルは特定の検索サービスや他社スキルを必須依存としない。利用環境にあるツールを使う。毎回読み込まれるかどうか、参照資料を適切に読むかどうか、操作結果を取得できるかどうかはホストの機能にも依存する。全応答で必要な短い原則は、利用環境の常時指示へ置く方法もある。

本文だけで別のモデルや独立した検証者を生成したり、検索や操作の実行を保証したりすることはできない。モデルやツール構成を変えたら、実際の環境で再評価する。最新版のプラン別提供条件は本資料では判定しない。

