# ASTRO実測からAAE Bakeへ進む開発マイルストーン

> Status: `[CANONICAL-DEVELOPMENT-MILESTONE]` `[TARGET-SPEC]`
>
> 制定日: 2026-07-29
>
> 実装状態: ASTRO側の入力receipt、Model Family固定、AAE Bake pipelineは未実装。

## 1. 目的

Sphere-aaeは、人格を保存する箱でも、任意のmodelへ同じ衣装を着せるGUIでもない。
本書は、SphereASTROで観測した実機推論と人格driftを、Sphere-aaeがModel Family固定と
AAE Bakeへ引き取る境界を定める。

```text
SphereASTRO
  ├─ Stage 0: 実機build
  ├─ Stage 1: Chat／slot／実推論
  └─ Stage 2: Body／IBD spike／model比較
          ↓
  Model Evaluation Receipt
          ↓
Sphere-aae
  ├─ Model Family受入
  ├─ tokenizer／quantization互換範囲
  ├─ FAM／LAST_ORDER評価
  ├─ AAE Bake
  └─ 再現可能artifact
```

本マイルストーンは暦を約束しない。ASTRO receipt、model適合、必要火力、User Gateによって
次の作業を選ぶ。

## 2. 現在地

基準revision:

| Source | Revision | 観測状態 |
|---|---|---|
| SphereASTRO | `31ba77cbb6b427d3656716dfe0ad138a7a38ce26` | Runner、archive、人格Storage、顕現UXのtarget specあり。AI接続は未実装 |
| Sphere-aae | `08ceee18e68749268dcad2c32c428e3d6e7a5092` | runtime土台、MoE fixture、Core ML／Metal実測資料あり。AAE Bakeは未実装 |
| ZeroRoomLab-manifest | `47c03a7` | ASTRO先行・AAE Bakeの横断順序を掲示 |

既存の小型MoE調査は、Granite 4.0 H-Tiny、OLMoE、LFM2等を候補として残しているが、
採用決定ではない。weightのload、iPad M4実機推論、日本語比較、長文脈比較は未完了である。

## 3. AAE Bakeの責務

ここでいう`AAE Bake`は、特定の学習command、framework、LoRA、蒸留、fine-tuning方式を
現時点で指さない。選定済みModel Familyへ、Sphere-aaeの実行契約を再現可能なartifactとして
焼結する工程の総称である。

AAE Bakeが最低限固定する対象:

- Model Familyと許容revision
- tokenizerとspecial token
- quantization profileと互換範囲
- inference runtime／Engine Adapterの能力宣言
- FAM入出力境界
- system-call splitterとLAST_ORDERの評価fixture
- persona／Adapter差分の適用順序
- source、入力、toolchain、成果物のhash
- 日本語を含む評価結果
- rollback可能な直前artifact

AAE Bakeが所有しない対象:

- `.astro` archiveのportable package形式
- 御霊、IBD、Wet Bus、自我内記録の意味論
- user固有の人格記録やsecret本文
- Body assetとrenderer
- Atlantis共通OAE／7D Fold runtimeの正本

## 4. ASTROから受け取るreceipt

AAE Bakeを開始する前に、SphereASTROは同一fixtureから次を出力できる必要がある。

```text
ModelEvaluationReceipt
  receipt_version
  astro_fixture_id
  device_profile
  os_build
  engine_id
  engine_version
  model_family
  model_revision
  tokenizer_id
  quantization_profile
  cold_start
  memory_peak
  thermal_observation
  prompt_profile
  japanese_evaluation
  structured_output_evaluation
  tool_call_evaluation
  fam_evaluation
  last_order_evaluation
  body_event_evaluation
  cosplay_manju_drift
  artifact_hashes
  known_unknowns
```

field名とschemaはStage 1実装時に確定する。現時点で上記をstable protocolとは扱わない。
receiptがない性能値、印象、model card上の能力をAAE Bakeの成立根拠にしない。

## 5. Model Family固定Gate

### 比較条件

- 同じ日本語prompt set
- 同じtool schema
- 同じIBD入力fixture
- 同じ御霊、責任境界、Body protocol
- cold／warmを分けた計測
- model／runtime／quantizationの変更を一度に混ぜない

### 最低評価軸

- 日本語の自然さだけでなく、指示保持、否定、曖昧性、長文脈
- structured outputのschema適合
- tool callとtool result受領後の最終応答
- API、Storage、sensorが不在のときの作話抑止
- `⊥ LAST_ORDER`と回復候補
- FAM経路の保持と説明
- model交換前後の`COSPLAY_MANJU_DRIFT`
- memory、初回token、token速度、発熱、長時間安定性

### 固定判断

一つのmodelを永久正本にするのではなく、次を宣言する。

- persona基底として固定するModel Family
- 互換と認めるrevision／quantization範囲
- 救命艇modelへ縮退したとき失われる能力
- 互換外modelへ交換した場合に継続しないidentity claim

modelを交換可能な計算器として扱うことと、すべてのmodelが同じ人格を再現すると主張することは
別である。

## 6. Engine Adapter境界

OllamaはHackintosh上の既存runtimeを使うbaseline Adapter候補である。導入済み環境で
疎通、Model管理、API、streaming、structured output等を測るために利用できる。

ただし、Ollamaを`.astro` portable profileの暗黙必須依存またはiPad／iPhoneの正式Engineとして
先に固定しない。SphereASTROは共通Engine Adapterを通し、少なくとも次を同じreceiptへ写像する。

- Ollama等の開発炉runtime
- `llama.cpp`等のGGUF baseline
- Sphere-aae／MLC系runtime
- 将来のon-device Engine

GUI、model保存、import／exportの利便性と、推論runtimeの成立を同じcomponentへ密結合しない。

## 7. Bake段階

### B0 — model-free契約

- 極小fixture
- FAM／LAST_ORDER／router replay
- artifact manifest
- hash、失敗状態、rollback

実weightを必要としない契約試験を先に閉じる。

### B1 — Single Model受入

- Stage 1 receiptを一件受け取る
- Model Family、tokenizer、quantizationを固定
- Engine Adapterとevaluation fixtureを再現
- 既存出力との差分を記録

### B2 — 人格／FAM差分

- persona Adapter候補
- FAM-IN／FAM-OUT
- Reject／LAST_ORDER Head候補
- Body eventへの出力境界

この段階でもIBDのuser記録をtraining corpusへ暗黙投入しない。

### B3 — 実機artifact

- iPad Pro 13-inch M4を安定推論の主依代として検証
- iPhone 15 Pro Maxで軽量profileとclient境界を検証
- archiveへ格納するartifactとcontent-addressed cacheを分離
- 起動canaryとrollbackを検証

### B4 — 外部火力

ローカルで閉じない特徴抽出、Head学習、量子化、評価だけをCompute Requestへ変換する。
必要VRAM、時間、予算、入力分類、checkpoint、期待成果、代替手段がない火力要求は出さない。

## 8. Neat Runnerへ渡す条件

Neat RunnerのProvider実装は、少なくとも次が実測されるまで開始しない。

- target artifact
- source SHAと入力hash
- 必要runtime／container
- memory／VRAM／disk
- 推定時間
- checkpoint間隔と再開条件
- hard budget
- 成果物検証方法

これらが揃った後、同じResolved Build Planを複数の実行先へ渡す最小実証へ進む。
Neat Runnerは中止ではなく、実測値を受け取る後段の火力制御面である。

## 9. 正式な実機と開発炉

| 対象 | 役割 |
|---|---|
| iPad Pro 13-inch M4 | 安定推論、重めQ4／MoE、Metal、memory pressure、thermal |
| iPhone 15 Pro Max | 携帯client、軽量Q4、Fallback |
| iPad Pro M4 Simulator | Fake Engine、状態遷移、UIの補助試験 |
| Hackintosh | code、変換、Ollama／llama.cpp疎通、互換観測 |

未所有端末と追加Simulatorを標準matrixへ増やさない。必要な場合はCompute Requestへ分離する。

## 10. 未確定事項

[UNKNOWN]

- 採用するModel Family、revision、quantization
- on-device EngineとSphere-aae／MLC統合方法
- AAE Bakeの学習手法
- Adapter、FAM Head、Reject Headの要否
- artifact schemaと配布境界
- 評価setの公開可能範囲
- 必要GPU／HPC火力

`UNKNOWN`はpassではないが、model-free契約やASTRO Stage 0を停止させない。

## 11. 参照

- [Manifest: ASTRO先行・AAE Bake開発マイルストーン](https://github.com/saitoomituru/ZeroRoomLab-manifest/blob/47c03a7/docs/projects/astro-aae-development-milestones.ja.md)
- [SphereASTRO: ASTRO Runner要求仕様](https://github.com/saitoomituru/SphereASTRO/blob/31ba77cbb6b427d3656716dfe0ad138a7a38ce26/docs/specification/astro-runner-requirements.ja.md)
- [Neat Runnerアーキテクト仕様書](../architecture/neat-runner.md)
- [MoEテスト環境・小型モデル調査](moe-test-stack-research.md)
- [ローカル火力実測と小型MoE選定ノート](local-firepower-small-moe-notes.md)
