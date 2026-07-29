# X99 HackintoshでのmacOS x86_64ビルド

Sphere-aaeのmacOSネイティブランタイムは、NinjaとMetalを使うCMake Presetでビルドできます。

> **実機identityの注意:** この文書の主検証機はApple製Mac Proではなく、Intel X99プラットフォーム上にmacOSを構成したHackintoshです。`system_profiler`が返す`Mac Pro (2019) / MacPro7,1`は、macOS互換動作のために提示しているSMBIOS identityであり、物理機種の証明ではありません。ファイル名`macos-intel.md`は既存リンク互換のため維持しています。

本書でいう「動作」「互換」「PASS」は、記録したハードウェア、コミット、負荷、ログの範囲で機能を観測したという意味です。Apple純正ハードウェアとの内部一致、ファームウェア同一性、Secure Boot、暗号強度、耐攻撃性を保証する表現ではありません。

## 必要なツール

- CMake 3.24以上
- Ninja
- Xcode Command Line Tools（Clang、Metal SDK）
- Rust / Cargo（tokenizers-cppのビルドに使用）
- Git（サブモジュールを含む）
- Python 3.11または3.12（Pythonパッケージを作る場合）

既定のPythonが3.13以降でもC++ランタイムはビルドできますが、PyTorch、TVM、モデル変換系パッケージの対応状況を考慮し、Python環境は3.11または3.12へ分離してください。

```bash
git submodule update --init --recursive
cmake --preset macos-metal
cmake --build --preset macos-metal
ctest --preset macos-metal
```

Metalを使わないCPU専用ビルドは、`macos-metal` を `macos-cpu` に置き換えます。

Python環境の例:

```bash
/usr/local/opt/python@3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
```

依存パッケージを導入すると数GB以上を消費する場合があります。モデルの重みと変換後成果物はさらに大きいため、作業前に空き容量を確認してください。

## X99 Hackintosh実機の構成

2026-07-14のビルド・Core ML試験時点の構成に、2026-07-15のidentity再確認を加えています。

| 項目 | 構成 |
|---|---|
| 物理プラットフォーム | X99ベースの自作PC / Hackintosh（Apple純正Macではない） |
| macOS提示identity | `Mac Pro (2019)` / `MacPro7,1`。SMBIOS互換identityであり物理モデル名ではない |
| CPU | Intel Core i7-5820K、3.3 GHz、6コア / 12スレッド、AVX2 + FMA |
| メモリ | 64 GB |
| GPU | AMD Radeon RX 5500 XT、device ID `0x7340`、VRAM 4 GB、PCIe x16、Metal対応 |
| OS | macOS 15.7.7 / Darwin 24.6.0 / x86_64 |
| ツール | CMake 3.31.3、Ninja 1.12.1、Apple Clang 16、Xcode 16.2、Rust 1.93 |
| 互換kext | Lilu 1.7.2、WhateverGreen 1.7.1、VirtualSMC 1.3.8、RadeonSensor 0.3.3 |
| GPU driver stack | Apple `AMDRadeonX6000` / Framebuffer / HWServices 7.0.0、HWLibs 1.0 |

`USE_METAL=ON`、`USE_LLVM=OFF`、`BUILD_CPP_TEST=ON` の構成で、共有ライブラリ、静的ライブラリ、C++テスト実行ファイルのx86_64ビルドとテスト2件の通過を確認しています。実モデルを使った推論速度とMetalカーネルの動作は、この検証には含まれません。

## Apple framework機能互換ライン

この環境では、Sphere-aaeのMetal backendに加えて、macOS組み込みのApple製ML・数値演算frameworkをx86_64 + AMD GPU向けビルドラインとして利用できます。ここでの`native`はmacOS frameworkを直接呼び出す実行形式を指し、Apple製ハードウェアであることや純正Macとの完全同一性を指しません。

2026-07-14に次を実測しました。

- AMD Radeon RX 5500 XTをMetal deviceとして取得
- `MTLDevice.supportsFamily(.metal3) == true`
- `xcrun metal` 32023.404でAIR target向けcompile toolchainを確認
- `MPSSupportsMTLDevice`がRX 5500 XTに対して`true`
- Core ML frameworkをloadし、`MLComputeUnits.cpuAndGPU`を選択可能
- Accelerate/vDSPのベクトル演算を実行
- IORegistry上にApple Neural Engine deviceは見つからない

従って、このマシンではANEを必須にせず、Metal / Metal Performance Shaders / Core MLのCPU+GPU / Accelerateを検証対象にします。

FAM非接続の固定MLPを使ったsmoke testでは、Core ML `cpuOnly` / `cpuAndGPU`の推論結果一致、MPS行列積、Accelerate/vDSPを確認しました。極小fixtureのp50はbatch 1でCPU-only 0.1970 ms、CPU+GPU 0.2189 ms、batch 256でCPU-only 0.1898 ms、CPU+GPU 0.3160 msでした。この規模ではCPUが速い一方、GPU実行の可否は独立MPS testで確認しています。

このCPUにAVX-512はありません。CPU高速経路を説明するときはAVX2 + FMAまたはAccelerateと表記します。実測の解釈と次の小型MoE候補は[ローカル火力実測と小型MoE選定ノート](local-firepower-small-moe-notes.md)を参照してください。

OBS Virtual Cameraと`OND800 -> SAO800`ラインの日常稼働は、macOSの映像・音声I/Oを含むend-to-end運用証跡として別枠で扱います。これはCore ML数値試験のPASSや純正Mac互換性を代替する証拠にはしません。

## この記録が証明する範囲

記録した負荷範囲では、次の機能再現を確認しています。

- X99 / Core i7-5820K / RX 5500 XT上でのSphere-aae x86_64ビルド
- Apple Metal toolchainによるAIR target向けcompile
- RX 5500 XTのMetal device取得、Metal 3 family応答、MPS実行
- Core MLのmodel compile、load、`cpuOnly` / `cpuAndGPU`推論
- Accelerate/vDSP実行
- FAM未接続HEADのbuild、load、observe-only実行と上流応答非干渉

次は未証明または本記録の対象外です。

- Apple純正Mac Proとのハードウェア、firmware、byte単位の完全同一性
- `cpuAndGPU`指定時の全operationのGPU配置
- Apple Neural Engine、T2、Apple Silicon固有経路
- Secure Boot、暗号強度、耐攻撃性、Appleのセキュリティ保証との同等性
- 実weight MoEの学習、長時間連続負荷、全macOS x86_64環境での普遍的互換性

追加結論には実機と原ログの確認が必要です。観測済みの機能を弱めず、未観測範囲へも拡張しないことを本ノートの境界とします。

詳細は[MoEテスト環境・小型モデル調査](moe-test-stack-research.md)、[Core ML火力を含むMoEテスト計画](coreml-moe-test-plan.md)、[ローカル火力実測と小型MoE選定ノート](local-firepower-small-moe-notes.md)を参照してください。

## 現実的な利用範囲

- C++ランタイム、FAMルーティング、LAST_ORDER、API層の開発と単体テスト: 十分可能
- Metalバックエンドのコンパイルと小型モデルの検証: 可能。まず1B〜3B級の4bit量子化モデルを推奨
- 7B級のGPU常駐: 4 GB VRAMでは重みだけで上限に近く、KVキャッシュ等を含めると実用的ではない
- CPU推論: 64 GB RAMにより7B〜13B級の量子化モデルは容量上は扱えるが、6コアCPUのため速度評価が必要
- 30B級以上やMoE全体の学習: GPUメモリと演算性能の面で対象外
- 小型ルーター、分類器、adapterの試作: モデルを小さく保てば可能
- CUDA、FlashAttention、ROCm: このmacOS / AMD構成では対象外。FlashAttention前提でビルドされたモデルも使用不可
- iOS向けクロスビルド: Xcode環境は利用可能だが、署名、実機、モデルパッケージを含む別検証が必要

GPUの4 GB VRAMより先に、ストレージが制約になる場合があります。検証時の空き容量は約73 GiB、ソースツリーは約1.5 GiB、Metalテストビルドは約815 MiBでした。複数モデルの重み、変換前後の複製、Python環境を同時に保持する場合は、少なくとも100〜200 GiB程度の空きを確保することを推奨します。

## 既知の警告

- `libflash_attn` がない警告は、この構成では想定内です。
- Xcode 16ではMetal APIの非推奨警告が出ますが、現時点ではビルドを妨げません。
- Rustで作られるtokenizersの一部オブジェクトについてmacOS 15.2 / 15.0のdeployment target警告が出ます。現在の実機ではリンクできますが、古いmacOSへ配布する場合はdeployment targetを統一してください。
