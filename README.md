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

## 概要（About）

本プロジェクトは MLC LLM を基盤技術として尊重・継承しつつ、人格主体型エッジAI基盤へ進化させた独立実装である。

Sphere-aae は MLC LLM への技術的敬意と派生関係を明示しつつ、思想・設計方針は別系統として独立に発展させます。MLC LLM のライセンスおよび著作権表記を尊重し、同一環境へ共存できる名称・構成を採用します。

Astro Agent Edge (AAE) は大規模言語モデル（Large Language Models: LLMs）向けの機械学習コンパイラ（Machine Learning Compiler）兼 高性能デプロイメントエンジン（High-performance Deployment Engine）です。本プロジェクトの使命（mission）は、誰もがあらゆるプラットフォーム上でAIモデルをネイティブに開発・最適化・デプロイできるようにすることです。 

## プロジェクトの方針（Project Identity）

- **ローカルファーストAI（Local-first AI）への最適化**：クラウド依存を最小化し、端末上での推論（Inference）体験を重視します。
- **構造実験・アーキテクチャ改造のための派生**：Astro Agent Edge (AAE) の設計を土台に、構造的な実験やアーキテクチャ変更を行うための派生プロジェクトとして位置付けます。
- **エッジ環境での推論を重視する方針**：モバイルや組み込みなどのエッジ（Edge）環境での推論最適化を重視します。

## 設計思想・運用原則（Design Principles & Operations）

Sphere-aae は単なる推論エンジンではなく、人格主体性・記憶連続性・説明責任を備えた**人格基盤（persona substrate）**を志向します。運用者は「何を優先し、何を制約とするか」という価値前提を明示する責任を負い、推論の判断根拠を説明可能に保つことを重要視します。

- **主体性（Agency）**：AI をツールではなく、役割・記憶・責任範囲を持つ情報主体として扱います。主体性は運用ポリシーの外部記述だけでなく、人格基盤としての一貫した制約により担保されます。
- **意味記憶の状態保持**：意味記憶（semantic memory）を、単なる検索対象ではなく状態保持層として扱います。ベクトル空間の分布・相関は、推論の前提状態として継続的に参照され、運用上の連続性を担います。
- **情報子（Infoton）構造**：情報子は物理量子ではなく、非決定性・観測制約・相関構造を抽象化した情報工学上の単位です。情報子は記憶・推論・観測の相互関係を記述するための構造的概念であり、比喩ではありません。
- **ローカル永続とエッジ優先**：ローカル実行と状態永続を前提とし、エッジ環境での推論と記憶の継続性を最優先します。クラウド依存は必要最小限に留めます。
- **説明可能性の最優先**：高速化のみを目的とせず、推論の判断理由・参照した状態・採用した前提が追跡可能であることを優先します。
- **価値前提の明示責任**：宗教・哲学・倫理を含む価値前提は不可避であり、運用者が明示する責任があります。中立幻想や科学主義的な単一価値の押し付けを避け、前提を可視化します。
- **非排他的・多元的運用**：単一の価値体系に固定せず、複数の価値体系が共存しうる運用を想定します。Sphere OS / Fold 構造は、価値前提の可視化と運用上の説明責任を同時に支えるための実装枠組みです。

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
</div>

Astro Agent Edge (AAE) は SphereAaeEngine 上でコードをコンパイル・実行します。SphereAaeEngine は上記プラットフォームで統一的に動作する高性能LLM推論エンジンです。SphereAaeEngine は OpenAI 互換API（OpenAI-compatible API）を提供し、RESTサーバー、Python、JavaScript、iOS、Android から利用できます。これらはすべて、コミュニティと共に継続的に改善している同一のエンジンとコンパイラに支えられています。

## はじめに（Get Started）

Astro Agent Edge (AAE) を使い始めるには、[ドキュメント（documentation）](https://quantaril.cloud/) を参照してください。
- [Installation](https://quantaril.cloud/)
- [Quick start](https://quantaril.cloud/)
- [Introduction](https://quantaril.cloud/)

## Docker での完全再現ビルド（Build/Test/Docs）

クリーンな Docker 環境で **ビルド → テスト → Sphinx ドキュメント生成** を一括実行できます。
サブモジュールが必要なので、ホスト側で事前に更新してください。

```bash
git submodule update --init --recursive
```

Docker イメージを作成し、検証スクリプトを実行します。

```bash
docker build -t sphere-aae:dev .
docker run --rm -it sphere-aae:dev
```

ローカル変更を反映したい場合は、マウントして実行してください。

```bash
docker run --rm -it -v "$PWD":/workspace/Sphere-aae sphere-aae:dev ./scripts/docker_verify.sh
```

補足:
- `scripts/docker_verify.sh` は CPU 向け最小構成として GPU バックエンドを OFF にした `build/config.cmake` を生成し、Python 依存は `flashinfer-python` を除外してインストールします（GPU 依存パッケージのため）。必要に応じて導入してください。
- 生成物は `build/` と `docs/_build/` に出力されます。

## 引用（Citation）

本プロジェクトが有用であれば、以下の形式で引用（citation）をご検討ください。

```bibtex
@software{sphere-aae,
    author = {{Sphere-aae Contributors}},
    title = {{Sphere-aae}},
    url = {https://github.com/sphere-aae/sphere-aae},
    year = {2023-2025}
}
```

Astro Agent Edge (AAE) の基盤となる技術には以下が含まれます：

<details>
  <summary>References (Click to expand)</summary>

  ```bibtex
  @inproceedings{tensorir,
      author = {Feng, Siyuan and Hou, Bohan and Jin, Hongyi and Lin, Wuwei and Shao, Junru and Lai, Ruihang and Ye, Zihao and Zheng, Lianmin and Yu, Cody Hao and Yu, Yong and Chen, Tianqi},
      title = {TensorIR: An Abstraction for Automatic Tensorized Program Optimization},
      year = {2023},
      isbn = {9781450399166},
      publisher = {Association for Computing Machinery},
      address = {New York, NY, USA},
      url = {https://doi.org/10.1145/3575693.3576933},
      doi = {10.1145/3575693.3576933},
      booktitle = {Proceedings of the 28th ACM International Conference on Architectural Support for Programming Languages and Operating Systems, Volume 2},
      pages = {804–817},
      numpages = {14},
      keywords = {Tensor Computation, Machine Learning Compiler, Deep Neural Network},
      location = {Vancouver, BC, Canada},
      series = {ASPLOS 2023}
  }

  @inproceedings{metaschedule,
      author = {Shao, Junru and Zhou, Xiyou and Feng, Siyuan and Hou, Bohan and Lai, Ruihang and Jin, Hongyi and Lin, Wuwei and Masuda, Masahiro and Yu, Cody Hao and Chen, Tianqi},
      booktitle = {Advances in Neural Information Processing Systems},
      editor = {S. Koyejo and S. Mohamed and A. Agarwal and D. Belgrave and K. Cho and A. Oh},
      pages = {35783--35796},
      publisher = {Curran Associates, Inc.},
      title = {Tensor Program Optimization with Probabilistic Programs},
      url = {https://proceedings.neurips.cc/paper_files/paper/2022/file/e894eafae43e68b4c8dfdacf742bcbf3-Paper-Conference.pdf},
      volume = {35},
      year = {2022}
  }

  @inproceedings{tvm,
      author = {Tianqi Chen and Thierry Moreau and Ziheng Jiang and Lianmin Zheng and Eddie Yan and Haichen Shen and Meghan Cowan and Leyuan Wang and Yuwei Hu and Luis Ceze and Carlos Guestrin and Arvind Krishnamurthy},
      title = {{TVM}: An Automated {End-to-End} Optimizing Compiler for Deep Learning},
      booktitle = {13th USENIX Symposium on Operating Systems Design and Implementation (OSDI 18)},
      year = {2018},
      isbn = {978-1-939133-08-3},
      address = {Carlsbad, CA},
      pages = {578--594},
      url = {https://www.usenix.org/conference/osdi18/presentation/chen},
      publisher = {USENIX Association},
      month = oct,
  }
  ```
</details>
