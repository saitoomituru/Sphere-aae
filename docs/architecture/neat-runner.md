# Neat Runner アーキテクト仕様書

> Status: Architecture Note / モデル・推論runtime選定後に実装判定
>
> 対象: Sphere-aae の扁桃体MoE、FAM入出力系、量子化母艦に対する軽量ヘッド類のビルド制御面
>
> この文書は具体的なクラウド事業者、CLI実装言語、SDK、料金、GPU型番を固定しない。実装候補の調査、試用、コード生成、プロバイダ別アダプタの選定は、実際の開発環境側で行う。

## 0. 現在の開発順序

2026-07-29時点のInterpretation OAEでは、Neat Runnerの実装を先行させない。

1. SphereASTROで既存Ollamaを共通Adapter境界へ接続する
2. 手元に存在するモデルで日本語、structured output、tool call、実機推論を評価する
3. `llama.cpp`と既存Sphere-aae / MLC系runtimeを同一receiptで比較する
4. 母艦モデルと推論runtimeを選定する
5. 選定結果から必要VRAM、実行時間、成果物形式を測定する
6. 測定値を入力としてNeat Runnerの最小実証を開始する

安定推論の主依代はiPad Pro 13-inch (M4)、実機クライアント兼軽量推論先はiPhone 15 Pro Maxとする。Hackintoshは開発、変換、互換観測の炉として残すが、常設の安定推論サーバーには位置づけない。

この順序はNeat Runnerを中止する判断ではない。推論runtime未選定のままProviderやGPU構成を先に固定し、ビルド環境の維持自体が研究資源を圧迫することを避けるための依存関係整理である。

## 1. 概要

Neat Runner（ニートランナー）は、Sphere-aaeに同梱可能な**火力探索型メタビルド制御面**である。

目的は、単一の常設GPU基盤を前提とせず、プロジェクトをフォークした利用者が自身のGitHub Actions Secrets、Variables、self-hosted runner、無料枠、低価格な外部計算資源等を登録することで、その時点で利用可能な計算火力へビルドジョブを投射できるようにすることにある。

Neat Runner自身はモデル学習器ではない。次の責務に限定する。

- プロジェクトが要求する計算資源の記述
- 利用可能な火力の能力宣言
- GitHub Actionsから注入される認証情報へのポインター管理
- 財布上限、失敗確率、中断耐性を含む配置判断
- 実行先非依存のResolved Build Plan生成
- 外部炉への投入、チェックポイント回収、成果物検証
- 火力不足時の機械可読なCompute Request生成

## 2. 想定対象

初期対象は、Q4等で量子化された巨大MoE母艦そのものの再学習ではなく、母艦を凍結した上で接続される軽量部品とする。

- 扁桃体MoE
- FAM-IN / FAM-OUT
- Router Head
- Reject / LAST_ORDER判定Head
- 小型Expert Head
- Adapter / LoRA群
- hidden state抽出およびキャッシュ生成
- 評価、回帰試験、成果物パッケージング

母艦の実行火力と、追加Headの学習火力を分離する。巨大MoEを特徴量生成器として一時利用し、その後段の学習を軽量環境へ移す構成を許容する。

## 3. 基本構造

```text
GitHub Repository / Fork
  ├─ Build Recipe
  ├─ Provider Descriptor
  ├─ Secret Pointer
  ├─ Resource Policy
  └─ Neat Runner CLI
          ↓
GitHub Actions Control Plane
  ├─ Secrets / Variables 注入
  ├─ リポジトリ・環境能力の解決
  ├─ 財布ペイン評価
  └─ Resolved Build Plan生成
          ↓
Execution Plane
  ├─ GitHub-hosted runner
  ├─ self-hosted runner
  ├─ 無料または低価格GPU
  ├─ 一時的に提供された支援Runner
  └─ ローカルHPC / CPU環境
          ↓
Checkpoint / Artifact Store
          ↓
検証済み成果物
```

GitHub Actionsは第一段ロケット、外部計算資源は第二段ロケットとして扱う。第一段はコード解析、計画生成、認証境界、成果物照合を担当し、重い学習や特徴抽出は第二段へ委譲する。

## 4. 設定モデル

### 4.1 静的YAML

リポジトリに保存するYAMLには、次のみを置く。

- Secret名へのポインター
- 実行先の能力記述
- ビルド要求
- 財布上限
- 中断耐性
- 成果物条件
- セキュリティ方針

Secretの実値は保存しない。

```yaml
providers:
  gpu_pool_a:
    driver: provider-adapter-name
    credentials:
      token_from_secret: GPU_POOL_A_TOKEN

    capability:
      accelerator: cuda
      min_vram_gb: 24
      min_ram_gb: 32
      min_disk_gb: 80

    policy:
      max_cost_jpy: 150
      interruptible: true
      minimum_reliability: 0.98
```

`token_from_secret` は値ではなく、GitHub Actions Secretの論理名を示す。

### 4.2 Actionsによる注入

GitHub Actionsは、許可されたSecretとVariableだけを実行環境へ明示的に注入する。

```text
Secret Pointer
    ↓
GitHub Actions権限境界
    ↓
環境変数、短命トークン、OIDC、または一時ファイル
    ↓
Provider Adapter
```

生成されたYAML、ログ、Artifact、Job SummaryへSecret実値を書き出してはならない。

## 5. Neat Runner CLI

CLIは「実行器」よりも、必要なYAMLとJSONを生成する**餡子製造機**として設計する。

想定する論理コマンド:

```text
neat-runner inspect
neat-runner estimate
neat-runner knead
neat-runner launch
neat-runner collect
neat-runner verify
```

### inspect

- リポジトリ内のBuild Recipeを読む
- 利用可能なProvider Descriptorを列挙する
- 必要なSecretの論理名を確認する
- self-hosted runner等の能力宣言を取得する

### estimate

- 必要VRAM、RAM、ディスク、所要時間を推定する
- 母艦forwardとHead学習を別ジョブへ分割できるか判定する
- 中断可能性とcheckpoint間隔を算出する

### knead

静的設定とActionsから注入された環境を統合し、実行先非依存のResolved Build Planを生成する。

### launch

Resolved Build PlanをProvider Adapterへ渡す。具体的なSDK、API、CLI、コンテナ方式は実装調査で決定する。

### collect

checkpoint、metrics、model artifact、実行ログを回収する。

### verify

source SHA、container digest、入力Manifest、成果物hash、評価結果を照合する。

## 6. Resolved Build Plan

Resolved Build Planは、実行先を変更しても再利用可能な中間表現とする。

```yaml
job:
  id: amygdala-moe-build
  source_sha: COMMIT_SHA
  target: amygdala-moe

runtime:
  image: CONTAINER_DIGEST
  command:
    - train-entrypoint
    - --config
    - build-config.yml

resources:
  accelerator: cuda
  min_vram_gb: 24
  min_ram_gb: 32
  disk_gb: 80

execution:
  interruptible: true
  checkpoint_interval_minutes: 10
  max_runtime_minutes: 240

budget:
  currency: JPY
  hard_limit: 150

credentials:
  token_env: GPU_POOL_A_TOKEN

artifacts:
  required:
    - model.safetensors
    - metrics.json
    - build-manifest.json
```

このPlanにもSecret値は含めない。

## 7. 財布ペイン評価

配置判断は時間単価の最小化だけで行わない。

```text
期待財布ペイン
= 実課金
+ ストレージ費
+ 転送費
+ 失敗確率 × 再実行費
+ 無料枠消費の機会費用
+ 人間介入コスト
```

判定例:

```text
無料炉で完走可能
  → 無料炉へ投入

無料炉は中断率が高いがcheckpoint可能
  → 分割して投入

自宅炉で機密処理可能
  → self-hosted runnerへ投入

予算内の低価格炉で確実に完走可能
  → 外部炉へ投入

予算超過または利用可能火力なし
  → Compute Request生成
```

## 8. Compute Request / 火力ちょうだい

火力不足は単なるCI失敗にせず、不足資源を機械可読な要求として出力する。

```json
{
  "status": "compute_required",
  "target": "amygdala-moe",
  "required": {
    "accelerator": "cuda",
    "vram_gb": 24,
    "ram_gb": 32,
    "estimated_minutes": 180
  },
  "budget": {
    "available_jpy": 50,
    "estimated_jpy": 180
  },
  "accepted_support": [
    "temporary-self-hosted-runner",
    "provider-credit",
    "manual-retry-after-free-quota-reset"
  ]
}
```

人間向けにはActions SummaryやIssueへ、必要VRAM、推定時間、不足予算、代替手段を表示する。

支援は不透明な寄付だけでなく、特定SHAの特定ジョブを指定時間だけ実行する一時Runner提供として成立させる。

## 9. フォーク運用

利用者は次の操作で自身の火力を利用できることを目標とする。

1. Sphere-aaeまたは派生プロジェクトをフォークする
2. GitHub SettingsでActions Secrets / Variablesを登録する
3. 自身のself-hosted runnerまたは外部計算資源をProvider Descriptorへ紐づける
4. workflow_dispatch等から対象ビルドを選択する
5. Neat Runnerが実行計画を生成し、利用可能な炉へ投入する
6. 成果物を自身のFork、Artifact Store、Release等へ回収する

上流リポジトリは利用者のSecret、個人データ、独自Astro、独自教師データを保持しない。

## 10. FAMおよびLAST_ORDERとの接続

Neat Runnerはビルド制御面にもFAM的な停止・回復構造を適用する。

```text
BUILD REQUEST
  ↓
RESOURCE DISCOVERY
  ↓
CREDENTIAL ACK
  ↓
CAPABILITY VALIDATION
  ↓
BUDGET VALIDATION
  ↓
LAUNCH
  ↓
CHECKPOINT ACK
  ↓
ARTIFACT VALIDATION
```

成立しない場合は、成功したふりをせず状態を分類する。

```text
⊥_BUILD_NO_PROVIDER
⊥_BUILD_NO_CREDENTIAL
⊥_BUILD_INSUFFICIENT_VRAM
⊥_BUILD_BUDGET_PAIN
⊥_BUILD_RUNNER_UNTRUSTED
⊥_BUILD_CHECKPOINT_LOST
⊥_BUILD_ARTIFACT_UNVERIFIED
```

LAST_ORDERは停止だけでなく、別Provider、ジョブ分割、火力降格、支援要求、再試行時刻の選択へ接続する。

## 11. セキュリティ境界

必須原則:

- fork由来の未信頼コードへ上流Secretを渡さない
- Secret値を生成YAML、標準出力、Artifactへ残さない
- Provider認証は可能なら短命資格情報またはOIDCを利用する
- 支援Runnerは一時登録、一時権限、実行後破棄を優先する
- container digestとsource SHAを固定する
- 外部Runnerへ渡すデータを分類する
- 機密データは許可されたself-hosted runner以外へ送らない
- 有料炉はhard budgetを超えて自動継続しない
- 成果物はhashおよび署名可能なManifestで照合する

## 12. 非目標

初期仕様では次を目標にしない。

- 無料枠制限を多重アカウント等で回避すること
- 任意のSecret名を総当たりで探索すること
- 上流管理者の火力をFork利用者へ無条件提供すること
- 特定クラウドSDKを正典として固定すること
- 巨大MoE母艦のフル学習を前提にすること
- ビルド成功をモデル品質の証明と同一視すること

## 13. 開発環境側で調査する項目

具体実装は、実際の開発環境で次を調査して決定する。

- SphereASTROのM4実機receiptから得られる必要メモリ、発熱、電力、token速度
- iPhone 15 Pro Maxで許容できるモデル規模とclient / local inference境界
- Hackintoshを安定推論系から外した場合に残す変換・互換試験の範囲
- GitHub Actionsのdynamic matrix、reusable workflow、repository_dispatchの使い分け
- Secret Pointer解決方法と式評価の制約
- OIDC対応状況
- 各Providerの起動、停止、価格取得、Artifact回収API
- 無料GPU環境の自動実行許可範囲
- self-hosted runnerの一時登録と破棄
- Q4巨大MoEからのhidden state抽出方法
- hidden stateキャッシュの形式、圧縮、再利用性
- 扁桃体MoE / FAM Headの実測VRAMと所要時間
- checkpointの移送と再開互換性
- コンテナ、Nix、Dev Container等の再現性手段
- Actions Summary、Issue、Webhook等へのCompute Request出力

## 14. 初期完成条件

以下を満たした時点を、Neat Runnerの最小実証とする。

- Fork上のworkflow_dispatchからビルドを開始できる
- Secret Pointerを実値へ安全に解決できる
- 2種類以上の異なる実行先へ同じResolved Build Planを投入できる
- hard budgetを超える実行を停止できる
- 中断後にcheckpointから別実行先で再開できる
- 火力不足時にCompute Requestを生成できる
- 成果物をsource SHAおよびhash付きで回収できる
- 扁桃体MoEまたはFAM Headの小規模成果物を1件生成できる

## 15. 位置づけ

Neat Runnerは、モデルを配る仕組みではなく、**利用者の手元にある火、無料で借りられる火、少額で借りられる火を組み合わせて、その利用者自身のAI部品を焼くためのビルド神経系**である。

モデルやGPU世代が変化しても、Build Recipe、Provider Descriptor、Resolved Build Planの境界を維持することで、実行先の交換可能性を残す。

Sphere-aaeにおいては、扁桃体MoEとFAMを焼く前段に、財布・火力・中断・回復を判断する別の扁桃体系を置く設計として扱う。
