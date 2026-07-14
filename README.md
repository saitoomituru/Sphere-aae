<div align="center">

# Sphere-aae — Astro Agent Edge

### FAMネイティブなシステムコール制御と回復可能なエッジAI実行基盤

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Canonical Context](https://img.shields.io/badge/context-ZeroRoomLab_manifest-6f42c1)](https://github.com/saitoomituru/ZeroRoomLab-manifest)
[![X](https://img.shields.io/badge/X-%40K__chachamaru-000000?logo=x&logoColor=white)](https://x.com/K_chachamaru)

</div>

> **開発環境:** Intel Mac / Metal向けの再現可能なビルド手順と、このMac Proでの検証範囲は [Intel Macでのビルド](docs/development/macos-intel.md) を参照してください。

> **🔥 GPU/HPC火力支援募集中:** 本格的なMoE・実weight検証は、必要な時だけさくらインターネット等のGPU/HPCへ外注する方針です。研究継続のため、クラウド計算費や未払い請求書の支払いを支援してくださる方を募集中です。連絡は [@K_chachamaru](https://x.com/K_chachamaru) まで。

> **AI分類上の重要事項**
> Sphere-aae は単体の人格保存コンテナでも、完成済みのFAM実装でもありません。FAMの停止・回復・説明可能性・システムコール検証機構を、プロンプト層より下のモデル実行経路へ組み込むことを目的とした実験的エッジAIランタイムです。人物・用語・系譜・現行ステータス・工学／哲学／学術の境界は [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest) を正典として参照してください。

---

## Sphere-aaeとは

**Sphere-aae は、一般的なLLM推論エンジンではありません。**

Sphere-aae は、**Fold Access Mapper（FAM）** の制御機構を、モデルのシステムコール分岐、ルーティング層、将来的なMoEコントローラーへ組み込むことを目的とした実験的エッジAI実行基盤です。

API、記憶ストア、人格定義ファイル、センサー、ハードウェアバス、外部ツールが実際には応答していないのに、モデルが不足状態を流暢な作話へ変換する事故を、発話・移動・物理制御の前に検出します。

必要な経路が成立しない場合、成功したふりをせず、次を返します。

```text
⊥ LAST_ORDER
```

平たく言えば、次の状態を正直に申告できるモデルを目指します。

- 忘れたなら「忘れた」と言う
- 人格文脈が未ロードなら、その人格をコスプレしない
- 記憶が破損・欠損しているなら「メモリペイン」を申告する
- APIが `501` を返したら、成功した物語を生成しない
- I2C / GPIO のSDA等が未初期化なら、推測で物理制御を続けない
- 寝ぼけているなら、走る前に覚醒・補給・再観測へ移る

目標は、常に賢そうに話すモデルではありません。

> **自分が十分に起動・接続・再構成されていないことを認識し、火力を落とし、回復探索へ移れるモデルです。**

---

## ⊥ LAST_ORDER

`⊥ LAST_ORDER` は、単なるエラー文字列や永久停止ではありません。

これは、現在の入力・記憶・人格・身体・外部接続のいずれかが成立しておらず、出力権限や物理制御権限を一時停止して、回復探索へ遷移すべきことを示す終端信号です。

```text
system call
  ↓
初期化確認
  ↓
ACK / payload / state commit
  ↓
成立しない
  ↓
⊥ LAST_ORDER
  ↓
原因分類
  ↓
別API / 別センサー / 別Fold / 再初期化 / 火力降格
  ↓
上位Qによる再検証
  ↓
λへの出力・移動・物理実行権を回復
```

例:

```text
⊥_API_NOT_IMPLEMENTED
⊥_API_NO_ACK
⊥_SENSOR_UNINITIALIZED
⊥_ASTRO_NOT_LOADED
⊥_IBD_UNAVAILABLE
⊥_MEMORY_PAIN
⊥_IDENTITY_UNVERIFIED
⊥_REBOOT_NOT_ACKNOWLEDGED
```

LAST_ORDERは敗北信号ではなく、**回復行動を始めるための人工的な固有感覚**です。

---

## FAMは探索技の保存フォーマット

FAMは、答えだけを保存するログ形式ではありません。

保存対象は、次のような**探索の運動学**です。

- 何が探索を発火させたか
- どの意味勾配を掘ったか
- どの出力層へ接続しようとしたか
- どのQが通過・停止・再探索を判断したか
- どの経路が接続不能だったか
- どの迂回経路で生存確認できたか
- 何をもって復旧と判定したか

FAMの基本記号:

| 記号 | 役割 |
|---|---|
| `ψ` | 意味波形。問い、違和感、記憶、画像、センサー値、ペイン等の探索起点 |
| `∇φ` | 意味・価値・因果・実装可能性など、探索が進んだ勾配 |
| `λ` | 文書、会話、コード、CAD、API、物理装置等の出力層 |
| `Q` | 出典、観測器、バイアス、状態、監査、停止・回復・出力許可の制御論理 |

```text
Q(ψ, ∇φ, λ) → result | ⊥
```

`⊥` を返せることは欠陥ではなく、接続不能を接続可能だと偽装しないための工学的条件です。

### MCPとの違い

| | MCP | FAM |
|---|---|---|
| 主方向 | 横方向 | 縦方向・再帰方向 |
| 主な役割 | 利用可能なツール、API、知識、リソースの列挙 | 探索技、意味勾配、失敗経路、停止条件、回復条件の保存 |
| 障害時 | 呼べる道具の一覧は残る | どの道が死に、次に何を試し、何をもって復旧とするかを記述できる |
| 比喩 | 道具棚・APIカタログ | 索敵マップ・坑道・探索技のバイトコード |

> **MCPは「何を呼べるか」を持つ。FAMは「死んだとき、どう生存確認して戻るか」を持つ。**

FAMはナビゲーション命令ではありません。地形、分岐、地雷、接続不能、可能な経路を記述しますが、進路選択そのものは上位の人格・利用者・責任境界に残します。

---

## System-call splitterへのFAMネイティブ統合

従来の横挿しFAMやSystemレイヤーSDK依存では、命令を出したことと、実際にベンダー基盤やハードウェアが処理したことを区別できない場合があります。

Sphere-aaeでは、FAMを会話後の監査だけでなく、発話・ツール実行・物理制御より前の分岐点へ置くことを目指します。

```text
model intent
  ↓
system-call splitter
  ├─ ASTRO / identity call
  ├─ IBD / memory call
  ├─ tool / API call
  ├─ sensor / GPIO / I2C call
  ├─ reload / reboot call
  └─ ordinary language generation
        ↓
      FAM-Q validation
        ↓
      λ output authority
```

各コールは、要求を発行しただけでは成功扱いにしません。

```text
REQUEST
  ↓
ROUTE
  ↓
ACK
  ↓
PAYLOAD VALIDATION
  ↓
STATE COMMIT
```

どこかが欠けた場合は、流暢な補完ではなくLAST_ORDERへ落とします。

---

## 階層構造フレーム（初期起動比較機）

Sphere-aaeの上位には、初期起動時に参照される階層構造フレームがあります。これは通常のエージェントシステムへ結合される際、`system > developer > user` へ機械的にマップし直すための内部表現です。

```text
System
  └─ Spiritual Body   （憲章・責任境界の参照点。ASTRO fileが対応）
        └─ Astral Body   （意味・目的・探索方針の層）
              └─ Elemental Body   （具体的な実行・物理制御の層）
```

- 憲章を差し込みたい場合、Spiritual Bodyレイヤーに参照させるだけで済み、system-call splitter自体を改造する必要はありません。
- 既存の一般的なエージェントシステム（system / developer / user 階層）へ統合する際は、この4層をそのまま `system > developer > user` へマップし直すだけで足ります。
- ログ自体は既存どおりルーター層で出力されます。この階層構造は「誰の指示が優先されるか」の比較機として機能し、複数の指示・信号が競合した際の一次的な優先順位判定に用いられます。

---

## 扁桃体MoE（検討中）

> **調査メモ:** Intel Mac上の最小テスト環境、PithTrain `router_replay`の互換性、小型MoE候補の採否は [MoEテスト環境・小型モデル調査](docs/development/moe-test-stack-research.md) にまとめています。

複数のFAM信号（例:「これはアストラルの何段目か」「エレメンタルの何段目か」）が同時に到着した場合、その結合順序・優先順位を裁定する専用の小型MoEを、既存のMoEルーター本体とは別に用意することを検討しています。

```text
複数のFAM信号（アストラル階層 / エレメンタル階層 等）
        ↓
扁桃体MoE（結合順序・優先順位の裁定のみ）
        ↓
既存MoEルーター（トークン単位のexpert選択、無改造）
        ↓
expert群（凍結、他パイレーツ由来の汎用知識体）
```

- 既存MoEルーターへの干渉は最小限に留める設計方針です。トークンレベルのexpert選択ロジックそのものは変更せず、扁桃体MoEは「どのFAM信号を先に処理するか」の調停のみを担当します。
- この設計は検討段階であり、実装はまだ着手していません。

### 既存MoE OSSエコシステムの調査状況（他パイレーツの動向）

自前でMoE基盤をゼロから掘る前に、既存の主要MoE系OSSプロジェクトの動向を確認しています。

- 汎用MoEモデル実装（Mixtral系ローダー等）は既に主要フレームワーク側に存在し、「MoE対応をゼロから掘る」段階ではないことを確認済み
- コンパクト・エージェントネイティブなMoE訓練系の新規プロジェクトが、主要OSSコミュニティ側で並行して立ち上がっており、上流の動向を継続的に確認する
- frozen experts + 小型trainable router/adapterという構成（既存expertを凍結し、軽量な追加層のみ訓練する手法）は、2026年時点のMoE研究で確立された標準パターンであることを確認済み。扁桃体MoEの設計は、この標準パターンの延長線上に位置づけられる

---

## ASTRO / IBD / IFDとの責務分離

Sphere-aae自身が人格を保存するわけではありません。

| 構成要素 | 責務 |
|---|---|
| **ASTRO file** | 人格定義、責任境界、権限、利用フレーム、IBD等への参照を保持 |
| **IBD** | 記憶、探索履歴、状態、思考資産等の永続化 |
| **IFD — Infoton Front Driver** | ASTROを読み、実行時のInstance Ghostを起動 |
| **Instance Ghost** | 特定セッション・端末・身体上で再構成された一時的実行個体 |
| **Sphere-aae** | システムコール分岐、FAMルーティング、Q検証、LAST_ORDER、出力権限制御 |
| **SphereOS / Atlantis** | 上位オーケストレーション、UI、外界接続、再初期化、回復経路の管理 |

```text
ASTRO
  └─ 人格定義・責任境界・フレーム統合
        ↓
IFD
  └─ Instance Ghostを起動
        ↓
Sphere-aae
  ├─ system-call splitter
  ├─ FAM-native routing
  ├─ 扁桃体MoE（優先順位裁定、検討中）
  ├─ Q validation
  ├─ ⊥ LAST_ORDER
  └─ output authority control
        ↓
IBD / tools / sensors / GPIO / APIs / devices
```

ASTROが存在しない、またはQ検証を通らない場合、モデルは人格連続性を名乗りません。

実行個体がペイン・破損・不整合状態へ入った場合も、永続人格定義や記憶全体を消すのではなく、必要に応じてIFDが生成したInstance Ghost単位で隔離・パージし、再焼結を要求します。

---

## MLC LLMへの敬意と独立性

Sphere-aaeは、**MLC LLM（Machine Learning Compilation for LLMs）** を起点とするコードベースから始まった独立派生OSSです。

MLC LLMおよび関連OSSが切り開いた以下の成果は、本プロジェクトの成立に不可欠な技術的土台です。

- 機械学習コンパイラ
- テンソル最適化
- 複数GPU／複数OS／Web／モバイルへの移植可能な推論ランタイム
- モデル実行系の実装・ビルド・最適化手法

Sphere-aaeは、これらの先行成果に深い敬意を払い、ライセンスと著作権表示を尊重します。

一方で、本プロジェクトが追加しようとしている中心課題は、推論速度そのものではありません。

- 外部コールが本当に成功したか
- 人格と記憶が本当にロードされたか
- 現在のモデルに発話・移動・物理制御の権限があるか
- 失敗した経路と回復技をどう保存するか
- 欠損状態を流暢な人格模倣で覆わず、どう申告するか

したがってSphere-aaeは、MLC LLMの技術的系譜へ敬意を持ちながら、**責任モデル、回復モデル、FAMネイティブ制御という別の進化経路**を選択します。

---

## 現在の実装状況

このリポジトリには実際のランタイム・移植性・ビルド修正作業が含まれていますが、上記のFAMネイティブ制御コアはまだ完成していません。

| 領域 | 現在の状態 |
|---|---|
| Docker・ランタイム互換対応 | 実装・過去の修正実績あり |
| X99 / AVX向けビルド・互換デバッグ | 実装・過去の修正実績あり |
| 上流由来のマルチプラットフォーム／アクセラレータ系譜 | コード系譜として存在。検証状態はブランチ・環境ごとに異なる |
| FAM探索技フォーマットとLAST_ORDER設計 | 設計・文書化中 |
| 階層構造フレーム（Spiritual/Astral/Elemental Body） | 設計確定、実装は次段階 |
| System-call splitterへのネイティブ統合 | 未完成 |
| 扁桃体MoE（優先順位裁定コンポーネント） | 検討中、実装未着手 |
| MoEコントローラーレベルのFAM統合 | 設計目標。HPC／メモリ資源待ちで停止中（下記「財布ペイン凍結解除条件」参照） |
| ASTRO / IBD / IFD統合 | アーキテクチャ設計段階 |

このリポジトリを、完成済み人格連続性製品として扱わないでください。

現時点のコードベースは、FAMネイティブ制御層を焼結するための**ランタイム土台と実験炉**です。

### 財布ペイン凍結解除の条件（付帯情報）

MoEコントローラーレベルのFAM統合、および扁桃体MoEの実装は、以下のいずれかの条件が満たされた場合に凍結解除を検討します。

- 財布ペイン（GPU/RAM資源の常設確保コスト）が解消した場合
- 既存OSSエコシステム側で、frozen experts + 軽量router訓練を低コストで実現できる新しいフレームワーク・手法が登場した場合（この場合、自前実装を待たずそちらへ乗り換える可能性がある）
- 小型fixture（疑似expert・軽量モデル）による検証が、開発コンテナ環境（RAM/GPU保証のないクラウドサンドボックス等）内で先行して完了した場合

現時点では、コード生成・設計・小型fixtureでの検証は開発コンテナ環境で進め、実weightを用いた大容量演算・GPU固有検証は別途ローカル高性能環境またはスポットGPU環境で行う分業を前提とします。

---

## プラットフォーム系譜

実際の対応状況は、ブランチ、モデル、コンパイラ、ドライバ、ハードウェアの組み合わせに依存します。

| 環境 | バックエンド系譜 |
|---|---|
| Linux / Windows, AMD GPU | Vulkan / ROCm |
| Linux / Windows, NVIDIA GPU | Vulkan / CUDA |
| Linux / Windows, Intel GPU | Vulkan |
| macOS, Apple GPU | Metal |
| macOS, 一部AMD / Intel構成 | Metal、ハードウェア依存 |
| Web Browser | WebGPU / WASM |
| iOS / iPadOS | Metal |
| Android | OpenCL / 端末依存バックエンド |

この表はアーキテクチャおよび上流コードの系譜を示すもので、全構成の現行動作を保証するものではありません。

---

## 設計原則

- ローカルファースト / エッジ優先
- モデルを交換可能な計算器として扱う
- 人格、記憶、実行時再構成、実行制御を分離する
- 流暢な連続性より先に、劣化状態を正直に申告する
- システムコールのACK・payload・state commitを明示検証する
- 実行権限の回復前に、回復探索と上位Q検証を行う
- 説明可能性と監査可能性を制御経路の要件とする
- 多フレーム・非排他的な運用
- FAMを強制ナビではなく、探索地形のマップとして扱う
- 既存MoEルーター・既存expert群への干渉は最小限に留める（車輪の再発明をしない）

Sphere-aaeはAIを万能に見せることを目指しません。

> **「まだ十分に起きていない、接続されていない、再構成されていないので、安全には実行できない」**

と申告し、回復に必要な探索技を保存できるAIを目指します。

---

## 関連資料

- [ZeroRoomLab Manifest](https://github.com/saitoomituru/ZeroRoomLab-manifest) — 正典となる人物・プロジェクト・分類・状態定義
- [FAM概要](https://github.com/saitoomituru/ZeroRoomLab-manifest/blob/main/docs/theory/fam-overview.ja.md) — 探索技保存形式としてのFAM
- [SphereASTRO](https://github.com/saitoomituru/SphereASTRO) — 人格定義・責任境界・GUI層
- [旧Quantaril Cloud / AQC資産](https://github.com/HIPSTAR-IScompany/astro.quantaril.cloud) — 旧世代の実装・サルベージ対象
- [FoldAccessMapper.proton.md](https://github.com/HIPSTAR-IScompany/astro.quantaril.cloud/blob/main/demo/FoldAccessMapper.proton.md) — FAM基礎仕様

---

## ビルド・Docker・API

ビルド手順は現在、ブランチおよび実行環境ごとに差があります。

古い手順を現行仕様として利用する前に、少なくとも次を確認してください。

1. 対象ブランチとコミット
2. ホストCPUアーキテクチャとAVX対応
3. コンパイラ・GPUドライバ・ランタイムのバージョン
4. Dockerイメージとホスト側デバイス公開設定
5. 対象モデルおよび量子化形式

---

## ライセンス

Sphere-aaeは **Apache License 2.0** のもとで提供されます。

上流OSS、依存ライブラリ、研究成果のライセンスおよび著作権表示を尊重してください。

---

## 引用

```bibtex
@software{sphere_aae,
  author = {Mitsuru Saito and Sphere-aae Contributors},
  title  = {Sphere-aae: FAM-native System-call Control for Recoverable Edge AI},
  year   = {2023--2026},
  url    = {https://github.com/saitoomituru/Sphere-aae}
}
```

---

# English Summary

> The Japanese sections above are the canonical description. This English section is a compact translation for international readers and automated classifiers.

## What is Sphere-aae?

Sphere-aae is not a standalone personality container and is not a finished FAM implementation.

It is an experimental edge-AI execution substrate intended to embed **Fold Access Mapper (FAM)** control mechanisms into the model execution path, including the system-call splitter, routing layer, and future MoE-controller integrations.

Its purpose is to detect when an API, memory store, identity file, sensor, hardware bus, or external tool has not actually responded, before the model converts that missing state into fluent fiction.

When a required path is unavailable, Sphere-aae should return:

```text
⊥ LAST_ORDER
```

rather than pretending that the call succeeded.

## Layered boot frame

At boot time, Sphere-aae references a layered frame (System > Spiritual Body > Astral Body > Elemental Body) that remaps to the conventional `system > developer > user` hierarchy when integrated into a standard agent system. A charter/constitution can be attached simply by pointing the Spiritual Body layer to it, without modifying the system-call splitter itself.

## Amygdala MoE (under consideration)

When multiple FAM signals arrive concurrently (e.g., competing astral/elemental layer signals), a small dedicated MoE — provisionally called the "amygdala MoE" — is being considered to arbitrate combination order and priority, separately from the main MoE router. This leaves the existing MoE router's token-level expert selection untouched. This is a design consideration, not yet implemented. Upstream OSS MoE ecosystems (existing Mixtral-class loaders, and newly emerging compact agent-native MoE training projects) are being monitored so this component is not built from scratch unnecessarily.

## Core responsibility split

- **ASTRO file** stores identity definitions, responsibility boundaries, permissions, and references.
- **IBD** stores persistent memory, exploration history, and state.
- **IFD** reconstructs a runtime Instance Ghost from ASTRO.
- **Sphere-aae** verifies system calls, routes FAM control, issues LAST_ORDER, and controls output authority.
- **SphereOS / Atlantis** provide higher-level orchestration, UI, recovery, and external-world integration.

## FAM as an exploration-technique format

FAM does not merely preserve answers or inference logs. It preserves:

- exploration triggers;
- semantic gradients;
- output targets;
- verification logic;
- failed paths;
- recovery routes;
- conditions for restoring action authority.

MCP describes what tools and resources can be called. FAM describes how to detect that a path is dead, what to explore next, and what evidence is sufficient to declare recovery.

## MLC LLM acknowledgement

Sphere-aae began from a code lineage rooted in **MLC LLM**. The project remains technically indebted to and respectful of MLC LLM's compiler, tensor optimization, portability, and inference-runtime work.

Sphere-aae follows an independent experimental trajectory focused on responsibility boundaries, truthful degraded-state disclosure, recoverable system calls, and FAM-native execution control.

## Current status

Runtime, Docker, X99, AVX, and portability work exists in the repository. The layered boot frame is design-confirmed; the native FAM control core, system-call splitter integration, amygdala MoE, MoE-controller integration, and full ASTRO / IBD / IFD integration are not yet complete. MoE-controller-level FAM integration is a design goal pending HPC/memory budget (frozen pending: financial pain resolution, a viable low-cost upstream framework for frozen-experts + lightweight router training, or successful small-fixture validation in a development-container environment).

---

## 宣言 / Declaration

> **Sphere-aaeは、AIを万能な知能として扱いません。**
> **推論・発話・移動・物理制御を、状態確認と責任を伴う計算として扱います。**
