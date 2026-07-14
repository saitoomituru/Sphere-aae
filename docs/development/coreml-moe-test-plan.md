# Core ML火力を含むMoEテスト計画

- 再検討日: 2026-07-14 (JST)
- 対象: `moe-test-edition`
- 状態: 実装前の採用案

## 結論

Core MLはLLM全体の代替runtimeではなく、**FAM信号から優先順位logitsを作る小型裁定器**の実行候補として採用する。Core MLの出力をhost側の決定的top-k adapterでexpert indexへ変換し、PithTrain互換の`router_replay`契約へ渡す。

```text
FAM signal vector
  -> Core ML tiny arbiter
  -> priority logits
  -> deterministic top-k adapter
  -> router_replay expert indices
  -> existing Sphere-aae MoE router / frozen experts
```

最初からQwenやOLMoE全体をCore MLへ変換しない。これにより、Core ML変換可否と既存MoE runtimeの正しさを分離する。

## 1. 実機で確認したApple ML経路

| 項目 | 2026-07-14の実測 |
|---|---|
| Core ML compute devices | AMD Radeon RX 5500 XT、CPU |
| Apple Neural Engine | device一覧に存在しない |
| Metal family | RX 5500 XTでMetal 3対応 |
| MPS | RX 5500 XTで利用可能 |
| Core ML compute policy | `cpuOnly` / `cpuAndGPU`を選択可能 |
| Accelerate | vDSP演算成功 |
| Core ML compiler | Xcode 16.2の`coremlcompiler` / `coremlc`あり |
| Metal toolchain | `metal` / `metallib` / `metal-objdump`あり |

`cpuAndGPU`はGPUの使用を許可する設定であり、各operationが必ずGPUへ配置される保証ではない。実際の配置判断は`MLComputePlan`のpreferred / supported compute deviceで記録する。小さすぎるモデルはdispatch overheadのためCPUが選ばれる可能性があるので、それ自体を失敗にはしない。

## 2. 周辺ライブラリの再選定

### 採用するもの

| ライブラリ / ツール | 役割 | 採用方法 |
|---|---|---|
| CoreML.framework | 小型裁定器のproduction候補 | macOS native、Swiftから利用 |
| coremltools 9.0 | MIL model生成、compile前検証、compute plan調査 | 専用Python 3.12環境へ固定 |
| Model Intermediate Language (MIL) | PyTorchを介さず極小MLPを生成 | 最初のfixture生成経路 |
| `coremlcompiler` | `.mlpackage`から`.mlmodelc`を生成 | Xcode同梱CLIを利用 |
| MetalPerformanceShadersGraph | Core MLとは独立したAMD GPU reference | 小型MLP / matmul比較に限定 |
| Metal Performance Shaders | top-k / matmul等のGPU primitive確認 | 必要な演算だけ利用 |
| Accelerate / vDSP | x86 CPU referenceと入力前処理 | native CPU基準 |
| XCTest | correctness、性能、メモリ回帰 | macOS専用test target |
| NumPy `.npz` | 小型weightとgolden vectorの交換 | pickleなし、backend共通fixture |

`coremltools 9.0`にはCPython 3.12 / macOS x86_64 wheelが存在する。Core ML環境は次のようにPyTorch reference環境から分ける。

```text
.venv-moe-reference
  Python 3.12
  torch 2.2.2
  transformers 4.48.2
  numpy < 2
  pytest

.venv-coreml
  Python 3.12
  coremltools 9.0
  numpy < 2
  pytest
```

第一段階ではMILから直接modelを作るため、`.venv-coreml`にPyTorchは不要である。学習済みrouterを持ち込む段階では、weightを`.npz`へ書き出し、同じMIL graphへ注入する。

### 保留するもの

| 候補 | 判断理由 |
|---|---|
| PyTorch -> Core ML直接変換 | `torch.jit.trace`は有力だが、Intel Mac最終版PyTorch 2.2.2との組合せを実測してから採用 |
| coremltools圧縮 / palettization | 数KB〜数MBの裁定器では効果が小さい。正しさ確立後に判断 |
| `CompiledMLModel` Python API | 初期load時間が問題になった場合に追加 |
| BNNS直接実装 | AccelerateとCore MLでCPU基準を作れるため初期段階では不要 |

### 初期環境から除外するもの

| 候補 | 除外理由 |
|---|---|
| ONNX / onnx-coreml | AppleがUnified Conversion APIへの移行を案内しており、onnx-coremlは更新停止 |
| TensorFlow | 小型裁定器に対して依存が大きく、PyTorch / MILとの二重管理になる |
| ExecuTorch | coremltools 9の対応対象だが、PyTorch 2.7世代とruntime追加を伴いIntel Mac制約に合わない |
| MLX | Apple Silicon向けで、このx86_64環境の検証対象外 |
| PithTrain本体 | CUDA 13 + Hopper / Blackwell前提。hook仕様だけ参照する |

## 3. 最小裁定モデル

第一fixtureは次の固定構造とする。

```text
input:  float32 [batch, 16]  # FAM signal vector
linear: 16 -> 32
SiLU
linear: 32 -> 4             # expert priority logits
output: float32 [batch, 4]
```

- 4 expert、top-2
- weightは固定seedで生成
- weightとgolden input/outputを`.npz`へ保存
- Core ML modelにはtop-kを含めない
- top-kはhost側adapterで実行し、tie時は小さいexpert IDを優先
- 境界値以外のgolden caseでは、順位差を誤差許容値より十分大きくする

Core ML内へtop-kを埋め込まない理由は、裁定器の浮動小数点誤差とindex契約の不具合を別々に検査するためである。

## 4. 改訂テスト計画

### T0: capability discovery

目的: 実行前提を機械可読に記録する。

- macOS / Xcode / Swift / Metal compilerのversion
- `MLComputeDevice.allComputeDevices`
- Metal device名、registry ID、Metal 3対応
- MPS device対応
- ANEの有無は情報として記録し、必須条件にしない

成功条件:

- CPUとAMD GPUをCore MLが列挙する
- MPSがRX 5500 XTをsupportする
- `coremlcompiler`とMetal toolchainを発見できる

### T1: artifact build smoke test

目的: 重いframeworkを使わず、再現可能なCore ML artifactを作る。

1. MILで固定MLPを生成
2. `.mlpackage`を保存
3. `coremlcompiler`で`.mlmodelc`へcompile
4. input/output名、shape、dtypeを検査
5. weight / model / golden vectorのhashを記録

成功条件:

- network不要で再compileできる
- artifactが小さくGit管理またはCI生成可能
- 同じseedから同じgolden vectorを再生成できる

### T2: Core ML correctness

同じgolden inputを次で実行する。

- NumPy reference
- Core ML `cpuOnly`
- Core ML `cpuAndGPU`

比較条件:

- float32: `atol=1e-5`, `rtol=1e-5`を初期値
- float16を導入した場合: `atol=1e-3`, `rtol=1e-3`を初期値
- top-2 expert indexは完全一致
- tie-break規則は完全一致

### T3: cross-backend parity

T2通過後に次を追加する。

- PyTorch 2.2.2 reference
- MPSGraph AMD GPU implementation
- Sphere-aae / TVM implementation

全backendでlogits、expert index、正規化weightを比較する。差が出た場合は、MLP、top-k、normalizationのどこで発生したかを段階的に特定する。

### T4: router replay契約

Core ML出力から作ったindexに対し、次を検査する。

- shape `[num_tokens, top_k]`を維持
- index範囲`[0, num_experts)`
- 同一token内の重複禁止
- replay無効時は元router出力を維持
- 不正shape、NaN、Inf、範囲外indexを拒否
- 置換後indexに対応するscoreを再取得
- 必要な場合だけweightを再正規化

### T5: Core ML火力計測

correctnessと性能を混ぜない。二つのprofileを使う。

| profile | shape | 目的 |
|---|---|---|
| latency | batch 1 | 日常のFAM裁定に近い応答時間 |
| throughput | batch 256以上 | GPUへ十分な仕事を与え、CPU/GPU差を観測 |

各profileで次を記録する。

- model compile / initial load時間
- warm-up後のp50 / p95 / p99 latency
- throughput
- peak resident memory
- `cpuOnly`対`cpuAndGPU`
- `MLComputePlan`のpreferred / supported device

初回は性能合否値を固定せずbaselineを採取する。二回目以降に回帰閾値を設定する。`cpuAndGPU`指定だけを根拠に「GPU実行済み」とは報告しない。

### T6: 日常運用との共存試験

OBS Virtual Cameraと`OND800 -> SAO800`ラインが動作している状態で、裁定器を一定時間反復する。

- 映像・音声のdropや切断がない
- Core ML inference errorがない
- latencyの外れ値とmemory増加を記録
- GPU競合時に機能が停止しない

これは手動または専用machine testとし、通常CIには入れない。OBS等をテストから自動起動・停止しない。

### T7: Sphere-aae統合

T0〜T4通過後にのみQwen2MoE gateへ接続する。

1. Core ML arbiterを独立componentとしてload
2. FAM signalを固定vectorへencode
3. logitsをdeterministic top-k adapterへ渡す
4. `router_replay`へindexを注入
5. 既存router / expert weightが変更されていないことを検査
6. Core ML unavailable時は既定routerまたはCPU referenceへ明示的に戻す

## 5. 実行レーン

| レーン | 実行内容 | 必須性 |
|---|---|---|
| portable CI | NumPy fixture、top-k、router contract | 全環境必須 |
| Intel Mac local | Core ML CPU/GPU、MPSGraph、Metal、TVM | この実機で必須 |
| Apple Silicon optional | ANEを含む`.all`比較 | 将来の互換確認 |
| CUDA cloud | PithTrain、実weight訓練、分散MoE | 必要時のみ |

Apple SiliconでのANE結果をIntel Macの成功条件へ混ぜない。一方、同じ`.mlpackage`とgolden vectorを使い、将来Apple Siliconでbackend差を追加測定できる形にする。

## 6. 実装開始判断

最初に実装する範囲はT0〜T2である。必要な追加物は、Core ML専用Python環境、MIL fixture生成script、Swift/XCTest smoke test、共通golden vectorに限定する。

T0〜T2の結果を確認するまで、次は行わない。

- 実weight MoEの取得
- Qwen全体のCore ML変換
- quantization / palettization
- PithTrain本体の導入
- Core ML componentのSphere-aae本線接続

### 火力実行時の保存・thermal policy

- CPU/GPU負荷を掛ける前に、作業ツリーをcommitし`moe-test-edition`へpushする。
- 未commit差分または未push commitがある場合、実行scriptは停止する。
- 実行中はAMD driverのIORegistry telemetryからGPU温度、activity、power、fan、VRAM、recovery countを記録する。
- 既定80 °Cでthermal guardを作動させ、対象workloadを終了する。
- CPU温度は非root CLIで取得できないため、取得不可であることをreportへ明記する。
- runごとに`logs/coreml/runs/<UTC timestamp>/`へ生ログとMarkdown reportを保存する。
- reportをcommitし、`moe-test-edition`へpushしてから次の負荷試験へ進む。
- OBS Virtual Camera等の日常系を自動で停止・再起動しない。

## 公式資料

- Core ML compute units: https://developer.apple.com/documentation/coreml/mlcomputeunits
- Core ML compute plan: https://developer.apple.com/documentation/coreml/mlcomputeplandeviceusage
- coremltools 9.0: https://github.com/apple/coremltools/releases/tag/9.0
- Core ML Tools PyTorch workflow: https://apple.github.io/coremltools/docs-guides/source/convert-pytorch-workflow.html
- Core ML MIL: https://apple.github.io/coremltools/docs-guides/source/model-intermediate-language.html
- Core ML conversion formats: https://apple.github.io/coremltools/docs-guides/source/target-conversion-formats.html
- MPSGraph: https://developer.apple.com/documentation/metalperformanceshadersgraph
- XCTest performance tests: https://developer.apple.com/documentation/xctest/performance-tests
