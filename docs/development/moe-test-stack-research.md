# MoEテスト環境・小型モデル調査

- 調査日: 2026-07-14 (JST)
- 対象ブランチ: `moe-test-edition`
- 対象機: Intel x86_64 Mac Pro、6コア / 12スレッド、RAM 64 GB、AMD Radeon RX 5500 XT 4 GB
- この文書の範囲: 実装前の採用判断。モデルweightの取得やPithTrain本体の導入はまだ行わない

## 結論

最初の実装は、実weightを使わない**極小Qwen2MoE fixture**で行う。Sphere-aaeにすでに存在するQwen2MoEのgate直後へ、PithTrain PR #62と同じ形のrouter replay契約を追加し、CPUで固定expert選択を検証する。

実weightを使う第二段階の第一候補は `allenai/OLMoE-1B-7B-0125` のGGUF `Q4_K_M` とする。ただし、これはまずllama.cppで実MoEのメモリ・速度基準を取るために使い、Sphere-aaeへのOLMoEローダー追加とrouter replay統合を同時には行わない。

PithTrain本体は参照実装として追跡する。ローカルMacへそのまま導入する対象にはしない。

## 1. 現在利用できる基盤

Sphere-aaeには、MoE試験に再利用できる次の資産がすでにある。

- TVM Runtime / RelaxとMetalバックエンド
- XGrammar
- Qwen2MoE / Qwen3MoEのモデル、ローダー、量子化定義
- `MixtralExperts`
- `gating_softmax_topk`、expert dispatch、group GEMMなどのMoE演算
- Intel Mac向けCMake Preset: `macos-metal` / `macos-cpu`

2026-07-14に`moe-test-edition`上で次を再実行し、MetalビルドとC++テスト1件の通過を確認した。

```bash
cmake --build --preset macos-metal
ctest --preset macos-metal
```

一方、Qwen2MoE / Qwen3MoEのgateは現在、`gating_softmax_topk`の結果をそのままexpert dispatchへ渡しており、`router_replay`相当の差し込み口はまだない。既存Pythonテストにも通常精度のrouter replay試験はない。

## 2. PithTrainの位置づけ

調査対象は `mlc-ai/pith-train` v0.1.3で、router replayはコミット`9d6634b`（PR #62）に含まれる。

### router replay契約

PithTrainの契約は概ね次の形である。

```python
Callable[[topk_idx: Tensor[num_tokens, top_k]], Tensor[num_tokens, top_k]]
```

呼び出し順は次のとおり。

1. gate logitsをsoftmaxする
2. top-kのweightとexpert indexを求める
3. `router_replay(topk_idx)`でexpert indexを置き換える
4. 置換後のindexを使って元のsoftmax scoreからweightを`gather`する
5. 必要ならtop-k内でweightを再正規化する

同梱の`force_balance(num_experts)`は、入力と同じshapeを維持しながら、expert indexをround-robinで均等化するベンチマーク用実装である。

このhookが直接受け取るのはFAM信号や優先順位ではなく、最終的なexpert indexである。扁桃体MoEとの接続には、FAMの裁定結果を次の制約を満たすindexへ変換する薄いadapterが必要になる。

- shapeは`[num_tokens, top_k]`を維持する
- 値域は`0 <= expert_index < num_experts`
- 同一token内の重複expertを許すか禁止するかを明示する
- replay無効時は既存gate出力を完全に維持する

### このMacでPithTrain本体を使わない理由

PithTrain v0.1.3は次を必須としている。

- Python 3.12以上
- PyTorch 2.12以上
- CUDA 13以上
- NVIDIA Hopper (SM90) またはBlackwell (SM100)
- DeepGEMM、FlashAttention 4、Flash Linear Attention

このMacはPython 3.12を用意できるが、GPUはmacOS上のAMD MetalでありCUDAを利用できない。またPyTorchはmacOS x86_64バイナリの提供を2.2系で終了しており、PithTrainが要求する2.12以上と両立しない。従って本体のinstallやtrainingをローカル成功条件に含めない。

公式資料:

- PithTrain: https://github.com/mlc-ai/pith-train
- PithTrain paper: https://arxiv.org/abs/2605.31463
- PyTorch macOS x86_64廃止案内: https://dev-discuss.pytorch.org/t/pytorch-macos-x86-builds-deprecation-starting-january-2024/1690

## 3. 推奨するテスト環境

用途の異なる環境を混ぜず、3層に分ける。

### A. Sphere native層（必須）

既存のCMake / Ninja / TVM / XGrammar / Metal構成をそのまま使う。これは最終的なSphere-aae統合とC++ runtime回帰試験を担当する。

```bash
cmake --preset macos-metal
cmake --build --preset macos-metal
ctest --preset macos-metal
```

### B. 軽量reference層（必須）

Python 3.12の独立venvを使う。標準Python 3.14へは導入しない。

採用候補の固定値:

```text
python == 3.12.x
torch == 2.2.2
transformers == 4.48.2
numpy < 2
pytest
```

目的は次に限定する。

- 数MB以下のランダムweight極小Qwen2MoEをCPUで生成
- top-kとreplay後indexの期待値比較
- frozen expertとtrainable routerの勾配境界確認
- Sphere-aae側と同じfixtureを使うreference oracle

PyTorch 2.2.2にはPython 3.12 / macOS x86_64 wheelがある。Transformers 4.48系はQwen2MoEとOLMoEの両方を持つ。最新TransformersやPyTorchへ無条件追随せず、このreference層だけ互換版を固定する。

### C. 実weight推論層（任意、第二段階）

llama.cppのmacOS x64ビルドと、OLMoE GGUFを使う。llama.cppはMoE weightをCPUに置く`--cpu-moe` / `--n-cpu-moe`を持つため、4 GB VRAMに全expertを置かずに試せる。

この層は実MoEの速度・RAM使用量・出力健全性の基準取得用であり、PithTrain hookの検証環境ではない。

公式資料:

- llama.cpp: https://github.com/ggml-org/llama.cpp
- OLMoE GGUF: https://huggingface.co/allenai/OLMoE-1B-7B-0125-GGUF

### D. Apple native互換層（並行検証）

Core ML火力を含む周辺ライブラリの再選定と段階テストは、[Core ML火力を含むMoEテスト計画](coreml-moe-test-plan.md)に分離して管理する。

このHackintoshではApple Silicon専用経路だけを見るのではなく、Intel x86_64 + AMD GPUで利用できるApple純正APIを独立したビルドラインとして維持する。

2026-07-14の実測:

| 項目 | 実測結果 |
|---|---|
| Metal device | `AMD Radeon RX 5500 XT`を`MTLCopyAllDevices()`で取得 |
| Metal family | `supportsFamily(.metal3) == true` |
| Metal compiler | Apple metal 32023.404、AIR target `air64-apple-darwin24.6.0` |
| Metal Performance Shaders | `MPSSupportsMTLDevice(device) == true` |
| Core ML | frameworkのloadと`MLComputeUnits.cpuAndGPU`の選択に成功 |
| Accelerate | vDSPで`[1, 2, 3, 4]`の二乗`[1, 4, 9, 16]`を実行 |
| Apple Neural Engine | IORegistry上でANE deviceを検出せず。ANE前提の成功条件にはしない |

Appleのfeature tableでもAMD 5000-seriesはMetal 3対象である。Core MLでは`.all`が利用可能なcompute unitからOSへ選択を任せ、`.cpuAndGPU`はNeural Engineを使わずCPU/GPUへ限定する。このためテストでは暗黙fallbackだけに依存せず、`cpuOnly`と`cpuAndGPU`を明示して結果を比較する。

現時点で確認したのはframework/API/演算経路であり、`.mlpackage`を使ったCore ML実モデル推論は未確認である。最初のApple native smoke testは、数KB〜数MBの固定モデルで次を測る。

1. `cpuOnly`での推論成功
2. `cpuAndGPU`での推論成功と出力一致
3. MPS行列演算または畳み込みの実行
4. Metal shaderのAIR compileとcommand buffer実行
5. ANEを要求しなくても機能が成立すること

OBS Virtual Cameraと`OND800 -> SAO800`ラインの日常稼働は、映像・音声を含む周辺I/O互換性の運用証跡として記録する。ただしMoE数値テストの合否とは分離し、Apple native配信・エージェント入出力ラインのend-to-end試験で利用する。

公式資料:

- Metal feature tables: https://developer.apple.com/metal/capabilities/
- Metal Performance Shaders device support: https://developer.apple.com/documentation/metalperformanceshaders/mpssupportsmtldevice(_:)
- Core ML compute units: https://developer.apple.com/documentation/coreml/mlcomputeunits
- Accelerate / vDSP: https://developer.apple.com/documentation/accelerate/using-vdsp-for-vector-based-arithmetic

## 4. 小型MoE候補

| 候補 | 規模 | ローカル適性 | Sphere-aaeとの距離 | 判断 |
|---|---:|---|---|---|
| 極小Qwen2MoE fixture | hidden 64〜128、1〜2層、4 expert、top-2 | weight不要、CPUで高速 | 既存Qwen2MoEを直接利用 | **第一段階に採用** |
| OLMoE-1B-7B-0125 | 7B total / 約1B active、64 expert / top-8 | Q4_K_M約4.21 GB、64 GB RAMで射程内 | OLMoEローダーは未実装 | **実weight第一候補** |
| Qwen1.5-MoE-A2.7B | 14.3B total / 2.7B active、60 expert / top-4 | CPU容量上は可能だが初手には重い | Qwen2MoE実装が既存 | **統合第二候補** |
| Granite-4.0-H-Tiny | 7B total / 1B active | サイズは良い | Mamba2 + MoEで追加要素が多い | 今回は保留 |
| Qwen3-30B-A3B | 30B total / 3B active | 4 GB VRAMでは不適、CPUでも重い | Qwen3MoE実装が既存 | クラウド段階へ延期 |

OLMoEはApache-2.0で、学習コード・データ・checkpoint・ログまで公開されている。GGUF Q4_K_Mは約4.21 GBで、現状約70 GiBの空き容量にも収まる。ただし変換前weightは取らず、第二段階でもGGUF一種類だけに限定する。

公式資料:

- OLMoE model: https://huggingface.co/allenai/OLMoE-1B-7B-0125
- OLMoE paper: https://arxiv.org/abs/2409.02060
- Qwen2MoE仕様: https://huggingface.co/docs/transformers/model_doc/qwen2_moe
- Granite 4.0仕様: https://www.ibm.com/granite/docs/models/granite

## 5. 周辺ツールの採否

| ツール | 用途 | ローカル採否 |
|---|---|---|
| TVM / Sphere-aae MoE ops | 最終runtimeとMoE演算 | 採用済み |
| XGrammar | constrained generation | 採用済み、router試験からは分離 |
| Metal / MPS / Core ML / Accelerate | Apple native GPU/CPU互換ライン | 採用、ANEなしを前提に継続検証 |
| pytest + NumPy | hook契約とfixture試験 | 採用 |
| PyTorch 2.2.2 + Transformers 4.48.2 | CPU reference oracle | バージョン固定で採用 |
| llama.cpp | GGUF実weightのCPU/Metal基準 | 第二段階で採用 |
| PithTrain | router replay仕様、将来のGPU訓練 | 参照・クラウド用。ローカルinstall対象外 |
| DeepSpeed / Megatron-Core / MegaBlocks / Tutel | 大規模分散MoE訓練 | 初期ローカル環境から除外 |
| MLX | Apple Silicon向け | Intel Macのため除外 |
| bitsandbytes / CUDA FlashAttention | CUDA量子化・kernel | macOS AMDのため除外 |

## 6. 実装開始時の順序

1. Python 3.12のMoE reference venvとlockファイルを追加する。
2. Core ML専用Python 3.12環境とMIL生成経路を追加する。
3. 極小Qwen2MoE / FAM裁定fixtureを作り、通常top-kの決定性を確認する。
4. Core ML `cpuOnly` / `cpuAndGPU`とNumPyの出力を比較する。
5. PithTrain互換の`router_replay(topk_idx) -> topk_idx`契約テストを追加する。
6. 固定index、force-balanced、Core ML裁定、無効化の4ケースを通す。
7. FAM裁定結果からexpert indexを作るadapter契約を追加する。
8. 同じ契約をSphere-aaeのQwen2MoE gate直後へ接続する。
9. native Metal / CPU / Core MLテストを通した後にだけ、OLMoE Q4_K_Mを取得して実weight基準を測る。

## 7. 成功条件と停止条件

第一段階の成功条件:

- replay有効時だけexpert indexが期待値へ変わる
- replay後のweightが置換後indexに対応する
- replay無効時の出力が既存実装と一致する
- expert weightを凍結し、router / adapterだけへ勾配を限定できる
- CPUだけで数秒〜数十秒以内にunit testが終わる
- `macos-metal`の既存C++テストを壊さない

次のいずれかが起きたらローカルでの拡大を止め、さくら等のGPU環境へ分ける。

- PyTorch 2.2.2では再現できない新しいPithTrain APIが必要
- CUDA kernelそのものの正しさを検証する必要がある
- 7B totalを超えるweight学習が必要
- expert parallel / FSDP / NCCLが成功条件へ入る
- ローカル空き容量が40 GiBを下回る

## 採用判断

環境構成は「Sphere native + Python 3.12固定reference + 任意のllama.cpp実weight基準 + Apple native互換」の四層とし、モデルは「極小Qwen2MoE fixture -> OLMoE Q4 -> Qwen1.5-MoE」の順で進める。この構成なら、GPU購入前にrouter replayとFAM adapterの主要設計を検証しながら、Metal / MPS / Core ML / Accelerateを使うApple向けビルドラインも維持できる。
