# Issue Draft: [計画] Neat Runnerをモデル・runtime選定後の火力制御面として実装する

> Status: model-and-runtime-selection-wait
>
> 関連仕様: [`docs/architecture/neat-runner.md`](../architecture/neat-runner.md)

## 概要

Sphere-aaeへ同梱可能な、火力探索型メタビルド制御面 **Neat Runner（ニートランナー）** の調査・試作Issue。

このIssueでは具体コードを先に固定しない。実装言語、GitHub Actions構成、クラウド／無料GPU Provider、SDK、料金取得方法、Q4巨大MoEからのhidden state抽出方法は、実際の開発環境で調査・試用して決定する。

## 先行する作業

- [ ] SphereASTROへ既存OllamaをAdapter経由で接続する
- [ ] iPad Pro 13-inch (M4)を安定推論の主依代として実機receiptを取る
- [ ] iPhone 15 Pro Maxでclient / 軽量推論境界を確認する
- [ ] 手元モデルの日本語、structured output、tool callを同一条件で比較する
- [ ] `llama.cpp`と既存Sphere-aae / MLC系runtimeを比較する
- [ ] 母艦モデルと推論runtimeを選定する

上記が完了するまでNeat RunnerのProvider実装は開始しない。Hackintoshは開発、変換、互換観測に利用できるが、常設の安定推論サーバーとして要求しない。

ビルド環境、Simulator、GPU Providerを先に増やすことは非目標とする。手元実機で閉じない検証は、必要な実機、GPU時間、予算、期待成果をCompute Requestとして提示し、人間の承認後に実行する。

## 基本アイデア

```text
Fork
  ↓
GitHub Actions Secrets / Variablesへ自分の火力設定を登録
  ↓
第一段: GitHub Actionsが要求火力・資格情報・財布上限を解決
  ↓
Neat Runner CLIがResolved Build Planを生成
  ↓
第二段: 無料炉 / 爆安炉 / self-hosted runner / 支援Runnerへ投入
  ↓
checkpoint・成果物回収
```

CLIはモデル学習器ではなく、静的YAML、Secret Pointer、Actions注入値、火力詳細を混ぜて実行可能なYAML / JSONを生成する「餡子製造機」として扱う。

## 初期対象

- Q4巨大MoE母艦からのhidden state抽出
- 扁桃体MoE
- FAM-IN / FAM-OUT
- Router / Reject / LAST_ORDER Head
- 小型Expert Head
- Adapter / LoRA
- 評価、checkpoint、成果物検証

巨大MoE母艦のフル学習は初期対象外。

## 調査項目

- [ ] M4実機receiptから必要メモリ、発熱、電力、token速度を採取
- [ ] iPhone 15 Pro MaxとiPad Pro 13-inch (M4)の役割分担を確定
- [ ] GitHub Actionsのdynamic matrix / reusable workflow / repository_dispatch比較
- [ ] Secret Pointerの安全な解決方法
- [ ] Actions VariablesとSecretsの責務分離
- [ ] OIDCおよび短命資格情報の利用可否
- [ ] Provider Descriptorスキーマ案
- [ ] Build Recipeスキーマ案
- [ ] Resolved Build Plan中間表現
- [ ] hard budgetと財布ペイン評価
- [ ] 無料GPU環境への正規な投入方法
- [ ] 低価格GPU Providerの起動・停止・価格取得API
- [ ] self-hosted runnerの一時登録・破棄
- [ ] 支援Runnerを安全に受けるCompute Request形式
- [ ] Q4巨大MoEからのhidden state取得方法
- [ ] hidden stateキャッシュ形式と圧縮
- [ ] checkpointを別Providerへ移して再開できる条件
- [ ] source SHA / container digest / artifact hash検証
- [ ] Actions SummaryまたはIssueへの「火力ちょうだい」出力

## 最小実証条件

- [ ] Fork上のworkflow_dispatchから開始できる
- [ ] Secret値をYAMLやログへ残さずProviderへ渡せる
- [ ] 同一Build Planを2種類以上の実行先へ投げられる
- [ ] hard budget超過前に停止できる
- [ ] 中断後、別の実行先でcheckpointから再開できる
- [ ] 火力不足時に機械可読なCompute Requestを生成できる
- [ ] 扁桃体MoEまたはFAM Headを1件焼ける
- [ ] 成果物をsource SHAとhash付きで回収できる

## 設計上の境界

- 無料枠制限の不正回避や多重アカウント運用は対象外
- Fork由来の未信頼コードへ上流Secretを渡さない
- Secret名は明示的なPointerとして扱い、総当たり探索しない
- 有料火力はhard budgetを超えて自動継続しない
- ビルド成功とモデル品質評価は分離する

## LAST_ORDER候補

```text
⊥_BUILD_NO_PROVIDER
⊥_BUILD_NO_CREDENTIAL
⊥_BUILD_INSUFFICIENT_VRAM
⊥_BUILD_BUDGET_PAIN
⊥_BUILD_RUNNER_UNTRUSTED
⊥_BUILD_CHECKPOINT_LOST
⊥_BUILD_ARTIFACT_UNVERIFIED
```

失敗時は単に赤いCIで終了せず、別Provider、ジョブ分割、火力降格、支援要求、再試行へ接続する。
