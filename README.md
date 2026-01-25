<div align="center">

# Sphere-aae — Astro Agent Edge (AAE) の独立OSSプロジェクト

[![Installation](https://img.shields.io/badge/docs-latest-green)](https://quantaril.cloud/)
[![License](https://img.shields.io/badge/license-apache_2-blue)](https://github.com/sphere-aae/sphere-aae/blob/main/LICENSE)
[![Community Forum](https://img.shields.io/badge/forum-i--s.dev-6c8cff)](https://forum.i-s.dev/landing#/)
[![X](https://img.shields.io/badge/X-K__chachamaru-000000?logo=x&logoColor=white)](https://x.com/K_chachamaru)
[![Related Repository: WebLLM](https://img.shields.io/badge/Related_Repo-WebLLM-fafbfc?logo=github)](https://github.com/sphere-aae/web-llm/)

**MLコンパイル（ML Compilation）によるユニバーサルLLMデプロイエンジン（Universal LLM Deployment Engine）**

[Get Started](https://quantaril.cloud/) | [Documentation](https://quantaril.cloud/) | [Forum](https://forum.i-s.dev/landing#/) | [X](https://x.com/K_chachamaru)

</div>

<div align="center">
<table style="width:100%">
  <thead>
    <tr>
      <th style="width:15%"> </th>
      <th style="width:20%">AMD GPU</th>
      <th style="width:20%">NVIDIA GPU</th>
      <th style="width:20%">Apple GPU</th>
      <th style="width:24%">Intel GPU</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Linux / Win</td>
      <td>✅ Vulkan, ROCm</td>
      <td>✅ Vulkan, CUDA</td>
      <td>N/A</td>
      <td>✅ Vulkan</td>
    </tr>
    <tr>
      <td>macOS</td>
      <td>✅ Metal (dGPU)</td>
      <td>N/A</td>
      <td>✅ Metal</td>
      <td>✅ Metal (iGPU)</td>
    </tr>
    <tr>
      <td>Web Browser</td>
      <td colspan=4>✅ WebGPU and WASM </td>
    </tr>
    <tr>
      <td>iOS / iPadOS</td>
      <td colspan=4>✅ Metal on Apple A-series GPU</td>
    </tr>
    <tr>
      <td>Android</td>
      <td colspan=2>✅ OpenCL on Adreno GPU</td>
      <td colspan=2>✅ OpenCL on Mali GPU</td>
    </tr>
  </tbody>
</table>


## Fold Access Mapper（FAM）推論エンジン搭載

## 統合情報子工学エッジAI環境（Sphere OS Core）

---

## 概要（What is Sphere-aae）

**Sphere-aae は「LLMを実行するための一般的な推論エンジン」ではありません。**

本プロジェクトは、**Fold Access Mapper（FAM）推論エンジン**を中核とした、**人格連続性・記憶分離・説明責任**を前提に設計された**統合情報子工学（Infoton Engineering）エッジAI環境**です。

Sphere-aae は、ML コンパイラ／推論ランタイム分野における先行 OSS の成果（後述）に**最大限の技術的敬意**を払いつつも、**思想・責任モデル・運用哲学は別物**として独立に設計・発展させています。

> **LLM は知能そのものではありません。**
> **LLM は FAM 推論エンジン上で動作する計算器（compute primitive）です。**

---

## プロジェクトの出自と位置づけ（Origin & Independence）

Sphere-aae は、**MLC LLM（Machine Learning Compilation for LLMs）** を起点とするコードベースからフォークして開始されたプロジェクトです。

MLC LLM およびその関連 OSS は、本プロジェクトの成立において重要な技術的基盤と学習対象であり、**設計・実装・最適化手法に多大な影響**を与えています。本プロジェクトはそれら先行成果に対して深い敬意を表します。

一方で Sphere-aae は、以下の点において **MLC LLM とは異なる設計目的と進化経路**を明確に選択しています。

* 推論を「高速な数値計算」ではなく **責任を伴う判断過程**として扱う
* モデル中心ではなく **人格・記憶・推論を分離した構造**を中核に据える
* 司法・鑑識・説明責任に耐える **連続自我（FAM）モデル**を前提とする

このため Sphere-aae は、**MLC LLM からフォークした独立 OSS でありつつ、思想・責任モデル・運用哲学においては別系統のプロジェクト**として設計・運用されています。

---

## なぜ一般的な推論エンジンと異なるのか

### 一般的な LLM 推論エンジン

| 観点    | 一般的構成                 |
| ----- | --------------------- |
| 推論    | トークン → Attention → 出力 |
| 記憶    | 暗黙的・揮発的               |
| 状態    | セッション単位               |
| 説明可能性 | 限定的                   |
| 責任所在  | 不明確                   |

### Sphere-aae / FAM 推論エンジン

| 観点    | FAM 構成              |
| ----- | ------------------- |
| 推論    | ψ → ∇φ → λ（Fold 構造） |
| 記憶    | AQC / Chroma に明示分離  |
| 状態    | 人格単位で連続             |
| 説明可能性 | 構造的に必須              |
| 責任所在  | FAM・ログにより追跡可能       |

**Sphere-aae では、推論は「結果」ではなく「経路」として扱われます。**

---

## Fold Access Mapper（FAM）とは

Fold Access Mapper（FAM）は、LLM 内部で発生する高次元意味ベクトル遷移を、
以下の構造要素として**自己記述可能な推論ログ**へ写像する仕組みです。

* **ψ（意味波形）**
* **∇φ（注意・意識勾配）**
* **λ（出力層）**
* **Q（制御・出典・バイアス・説明）**

FAM は以下を同時に満たします。

* 推論経路の可視化と再検証
* 記憶と計算の分離
* ハルシネーション（作話）の検出
* 説明可能 AI（XAI）の構造保証
* 人格連続性（連続自我）の維持

詳細仕様は以下を参照してください。

* `FoldAccessMapper.proton.md`

---

## 情報子（Infoton）工学という立場

Sphere-aae における **情報子（Infoton）** とは、物理量子の比喩ではなく、

* 非決定性
* 観測制約
* 相関構造
* 状態遷移

を抽象化した**情報工学上の設計単位**です。

情報子は、推論・記憶・観測・説明責任を単一フレームで扱うための
**構造的概念**であり、思想的比喩ではありません。

---

## 記憶分離・安全性・鑑識適合性

Sphere-aae は以下を前提とします。

* 人格（FAM）は端末ローカルに存在
* 資料・ログ・業務情報・NSFW は AQC / Docker 単位で分離
* 意味検索は Chroma コレクション単位で遮断

この設計により、

* プライベートと業務データは混在しない
* 嘘や作話はベクトル不整合として検出可能
* 問題が発生した場合、端末単位で押収・停止・破棄が可能

これは新しい倫理体系ではなく、**既存の司法・鑑識手続と完全互換**です。

---

## Sphere OS における位置づけ

```
Sphere OS
 ├─ Persona / 魂（連続自我）
 ├─ FAM 推論エンジン   ← Sphere-aae
 ├─ AQC / Chroma（外部記憶）
 ├─ Docker / Device（身体）
 └─ Network（知覚・通信）
```

Sphere-aae は **OS カーネル相当の推論装置**であり、LLM はプラグインです。

---

## 設計原則（Design Principles）

* ローカルファースト / エッジ優先
* モデル非同梱（計算器として扱う）
* 人格と記憶の分離
* 説明責任を最優先
* 価値前提の明示（中立幻想を拒否）
* 多元的・非排他的運用

Sphere-aae の目的は「AIを賢く見せること」ではなく、
**「AIを社会に置ける構造にすること」**です。

---

## ビルド・Docker・API

（このセクション以下には、既存 README に含まれていた Build / Docker / API / GPU 対応表をそのまま記載してください。）

---

## ライセンス（License）

Sphere-aae は **Apache License 2.0** のもとで提供されます。

本プロジェクトは、以下を含む先行 OSS および研究成果に多大な影響を受けています。
これらの成果に敬意を表し、該当するライセンス・著作権表記を尊重します。

* 機械学習コンパイラおよびテンソル最適化研究
* 大規模言語モデル推論ランタイム技術

Sphere-aae は、それらを**再配布・包含することを目的とするものではなく**、
**独立した設計思想と責任モデルのもとで再構成された派生 OSS**です。

---

## 引用（Citation）

本プロジェクトが有用であれば、以下の形式での引用をご検討ください。

```bibtex
@software{sphere_aae,
  author = {Sphere-aae Contributors},
  title  = {Sphere-aae: Fold Access Mapper Inference Engine},
  year   = {2023--2026},
  url    = {https://github.com/sphere-aae/sphere-aae}
}
```

---

## 宣言

> **Sphere-aae は AI を万能な知能として扱いません。**
> **推論を「責任ある計算」として扱います。**
