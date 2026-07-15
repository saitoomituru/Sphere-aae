# ローカル火力実測と小型MoE選定ノート

- 作成日: 2026-07-14 (JST)
- 対象branch: `moe-test-edition`
- 対象機: X99ベースのx86_64 Hackintosh、Intel Core i7-5820K、6 core / 12 thread、RAM 64 GB、AMD Radeon RX 5500 XT 4 GB
- identity境界: macOSの`MacPro7,1`表示はSMBIOS互換identityであり、物理的なApple Mac Proを示さない
- 空き容量: 71 GiB（調査時点）
- 状態: FAM非接続の最小Core ML試験まで完了。実weight MoEは未取得・未実行

## 1. ここまでの実測

### CPU命令

`sysctl`で確認したCPU featureはAVX2、FMA、BMI1/2までで、AVX-512は存在しない。この機体のCPU高速経路は**AVX2 + FMA**またはApple Accelerateによるものであり、AVX-512と表記しない。

### Core ML最小fixture

FAMを接続せず、`16 -> 32 -> 4`の固定MLPをCore ML `cpuOnly` / `cpuAndGPU`で比較した。

| profile | batch | CPU-only p50 | CPU+GPU p50 | 判定 |
|---|---:|---:|---:|---|
| latency | 1 | 0.1970 ms | 0.2189 ms | CPUが約1.1倍高速 |
| throughput | 256 | 0.1898 ms | 0.3160 ms | CPUが約1.7倍高速 |

この結果が示すのは、極小処理ではGPU dispatchや配置判断のoverheadよりCPU経路が軽いということだけである。LLM全体や大きな行列でもCPUがGPUより速いとは結論しない。

別のMPS行列積はRX 5500 XTで誤差0、Accelerate/vDSPもPASSした。短時間run中のGPU telemetryは53–54 °C、19–21 W、812–816 RPM、GPU recovery 0、thermal abortなしだった。ただし各profile 1 sampleのsnapshotであり、連続負荷の熱安定性を示す値ではない。

生ログと詳細は[`logs/coreml/runs/20260714T033727Z/REPORT.md`](../../logs/coreml/runs/20260714T033727Z/REPORT.md)を参照する。

## 2. 小型MoEは射程に入るか

**loadして短い日常会話とtool callを評価する段階は射程内**と判断する。ただし、現時点で実測済みなのは小型裁定器であり、実LLMのtoken生成速度は未測定である。従って「実用速度まで確認済み」ではなく「容量とruntime対応から、次に実測する価値がある」が正確な状態である。

64 GB RAMなら4–5 GBのQ4 GGUFとKV cacheを収容できる。一方、4 GB VRAMへQ4本体、KV cache、runtime bufferを全て常駐させる余裕はない。最初はexpert weightをCPU/RAMへ置き、共有層だけをMetalへ部分offloadする構成を基準にする。

## 3. 用途別の候補

| 優先 | model | total / active | Q4_K_M | 会話・拡張 | この機体での役割 |
|---:|---|---:|---:|---|---|
| 1 | Granite 4.0 H-Tiny | 7B / 1B | 4.23 GB | 日本語、structured chat、tool calling、Apache-2.0 | **日常会話＋tool拡張の第一候補** |
| 2 | OLMoE-1B-7B-0125-Instruct | 7B / 約1.3B | 4.21 GB | 主に英語、Apache-2.0、64 expert / top-8 | **MoE構造・router比較の第一候補** |
| 3 | LFM2-8B-A1B | 8.3B / 1.5B | 5.04 GB | 日本語、multi-turn、agentic / tool use | **edge会話の比較候補** |
| 4 | Qwen1.5-MoE-A2.7B-Chat | 14.3B / 2.7B | 約8 GB以上を想定 | Qwen2MoE実装との距離が近い | 上記成功後の統合候補 |
| 延期 | Qwen3-30B-A3B | 30B / 3B | 4 GB VRAMの範囲外 | Sphere-aaeにQwen3MoE資産あり | cloud / 増設後 |

### Granite 4.0 H-Tinyを先にする理由

- 64 expertから6 expertをactiveにする7B total / 1B activeのhybrid MoE
- 公式GGUFにQ3_K_M 3.35 GB、Q4_K_M 4.23 GBがある
- 日本語を対応言語として明記
- OpenAI function schema形式のtool calling例がある
- llama.cppで直接起動する公式手順があり、model変換を挟まずbaselineを取れる
- Apache-2.0で、後の検証成果を扱いやすい

Q3_K_Mはmodel fileだけなら4 GB未満になるためfit probeに使えるが、KV cacheとruntime bufferを含む全量のVRAM常駐は保証しない。会話品質を見る本命はQ4_K_Mとし、VRAM容量を超えるためCPU/RAM主体で開始する。

### OLMoEを残す理由

OLMoEは会話品質の第一候補ではなく、64 expert / top-8の通常Transformer MoEを追跡しやすいreferenceである。training code、data、checkpoint、logが公開されているため、router replayやexpert selectionを調べる対象として価値が高い。Instruct版の公式GGUF Q4_K_Mは4.21 GBだが、主言語は英語なので日本語の日常会話判定ではGraniteより後に置く。

### LFM2を比較候補にする理由

LFM2-8B-A1Bは8.3B total / 1.5B activeで、日本語、multi-turn conversation、agentic task、tool useを明記している。公式GGUFとllama.cpp手順もある。一方、18 convolution + 6 attentionの独自hybrid構造、5.04 GBのQ4、LFM Open License v1.0という差があるため、最初の一体にはしない。

## 4. MoEで回避できるもの・できないもの

MoEのtop-k routingで回避できるのは、主に**tokenごとの非選択expertの演算**である。

回避または削減できるもの:

- tokenごとの全expert同時計算
- active parameter相当を超えるexpert GEMM
- llama.cppの`--cpu-moe`を使ったexpert weightのGPU常駐
- 公式GGUF + llama.cpp baselineを使う場合の独自model変換

回避できないもの:

- 全expert weightのdownloadとstorage
- 通常runtimeでの全weightのmmapまたはRAM address space
- router、shared expert、attention、KV cacheの計算
- GraniteのMamba2やLFM2のconvolutionなど、architecture固有operationのruntime対応
- Sphere-aaeへnative統合する場合のloaderとoperator実装

従って「使わないexpertを計算しない」は正しいが、「使わないexpertをbuildもloadも一切しない」は一般には正しくない。llama.cppの`--cpu-moe` / `--n-cpu-moe`はexpertをCPUへ置けるが、必要になったexpertをdiskから都度buildする仕組みではない。

## 5. 次回の実weightテスト順序

weight取得と負荷試験は別指示で行う。実行前に必ずcommit / pushし、75 °C thermal guardとrun log保存を適用する。

### M0: model-free契約

- 極小router fixture
- Core ML / NumPy parity
- MPS / Accelerate smoke
- 状態: 完了

### M1: Granite load probe

- `Granite 4.0 H-Tiny Q4_K_M`
- context 2,048、batch 1、短い日本語prompt
- CPU-onlyを基準にし、次に`--cpu-moe` + Metal partial offload
- load時間、RSS、prompt processing、generation tok/s、初回token時間を記録

### M2: 日常会話＋拡張

- 日本語3 turn会話
- 事実質問と「不明」の扱い
- JSON固定出力
- 1 tool callとtool result後の最終回答
- 2K context内の短いRAG入力
- 100–300 token生成を複数回実行し、温度とlatency外れ値を記録

暫定的な会話速度の目安:

| generation速度 | 判断 |
|---:|---|
| 8 tok/s以上 | 軽い日常会話として良好 |
| 4–8 tok/s | 待てる範囲、edge agent候補 |
| 2–4 tok/s | 機能試験用 |
| 2 tok/s未満 | 日常会話の常用候補から外す |

これは性能合否の確定値ではなく、初回測定を分類する暫定値である。

### M3: MoE reference比較

- OLMoE Instruct Q4_K_Mで同じprofileを実行
- Graniteとの差をactive parameter、architecture、tool / 日本語品質で分離
- router traceが必要ならmodel本体の改造前にfixtureで再現

### M4: 代替edge model

- Graniteの品質または速度が不足した場合だけLFM2 Q4_K_Mを取得
- 3 modelを同時に保存せず、空き容量40 GiBを停止線にする

## 6. 現時点の判断

日常会話に軽いtool/FAM拡張を加える用途は、Granite 4.0 H-Tiny級で**実機試験の射程内**に入った。FAM裁定器自体は極小なのでCPU AVX2/FMA経路へ置き、LLM側はMoEのsparse expert計算とCPU/RAM + Metal partial offloadを使う構成が自然である。

高火力MoEは、この通常火力レーンでrouter契約、prompt、tool schema、fallback、logを固めた後に同じinterfaceのままcloudへscaleする。ローカル成功条件へtraining、CUDA kernel、expert parallelを混ぜない。

## 公式資料

- Granite 4.0 H-Tiny: https://huggingface.co/ibm-granite/granite-4.0-h-tiny
- Granite 4.0 H-Tiny GGUF: https://huggingface.co/ibm-granite/granite-4.0-h-tiny-GGUF
- OLMoE Instruct: https://huggingface.co/allenai/OLMoE-1B-7B-0125-Instruct
- OLMoE Instruct GGUF: https://huggingface.co/allenai/OLMoE-1B-7B-0125-Instruct-GGUF
- LFM2-8B-A1B: https://huggingface.co/LiquidAI/LFM2-8B-A1B
- LFM2-8B-A1B GGUF: https://huggingface.co/LiquidAI/LFM2-8B-A1B-GGUF
- llama.cpp CLI (`--cpu-moe` / `--n-cpu-moe`): https://github.com/ggml-org/llama.cpp/blob/master/tools/cli/README.md
- llama.cpp feature matrix: https://github.com/ggml-org/llama.cpp/wiki/Feature-matrix
