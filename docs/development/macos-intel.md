# Intel Macでのビルド

Sphere-aaeのmacOSネイティブランタイムは、NinjaとMetalを使うCMake Presetでビルドできます。

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

## このMac Proでの検証結果

2026-07-14に次の実機で確認しました。

| 項目 | 構成 |
|---|---|
| モデル | Mac Pro (2019, MacPro7,1) |
| CPU | Intel x86_64、3.3 GHz、6コア / 12スレッド |
| メモリ | 64 GB |
| GPU | AMD Radeon RX 5500 XT、VRAM 4 GB、Metal対応 |
| OS | macOS 15.7.7 |
| ツール | CMake 3.31.3、Ninja 1.12.1、Apple Clang 16、Xcode 16.2、Rust 1.93 |

`USE_METAL=ON`、`USE_LLVM=OFF`、`BUILD_CPP_TEST=ON` の構成で、共有ライブラリ、静的ライブラリ、C++テスト実行ファイルのx86_64ビルドとテスト2件の通過を確認しています。実モデルを使った推論速度とMetalカーネルの動作は、この検証には含まれません。

## Apple native互換ライン

この環境では、Sphere-aaeのMetal backendに加えて、Apple純正のML・数値演算frameworkをx86_64 + AMD GPU向けビルドラインとして利用できます。

2026-07-14に次を実測しました。

- AMD Radeon RX 5500 XTをMetal deviceとして取得
- `MTLDevice.supportsFamily(.metal3) == true`
- `xcrun metal` 32023.404でAIR target向けcompile toolchainを確認
- `MPSSupportsMTLDevice`がRX 5500 XTに対して`true`
- Core ML frameworkをloadし、`MLComputeUnits.cpuAndGPU`を選択可能
- Accelerate/vDSPのベクトル演算を実行
- IORegistry上にApple Neural Engine deviceは見つからない

従って、このマシンではANEを必須にせず、Metal / Metal Performance Shaders / Core MLのCPU+GPU / Accelerateを検証対象にします。Core MLの実モデル推論、`cpuOnly`と`cpuAndGPU`の結果一致、MPS kernel実行、Metal command buffer実行は次段のsmoke testとして追加します。

OBS Virtual Cameraと`OND800 -> SAO800`ラインの日常稼働は、Apple nativeの映像・音声I/Oを含むend-to-end運用証跡として別枠で扱います。

詳細は[MoEテスト環境・小型モデル調査](moe-test-stack-research.md)を参照してください。

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
