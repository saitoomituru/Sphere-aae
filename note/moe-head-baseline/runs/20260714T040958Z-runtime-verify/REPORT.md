# llama.cpp固定runtime検証結果

- 実行日時: 2026-07-14 04:09:58 UTC
- 判定: **PASS**
- 対象Git commit: `2a4edecebdead24e9638764fce329f0759bfc2f5`

## 確認結果

- 公式release `b9637`のmacOS x86_64配布物を取得した。
- archive SHA256は公式値`71743f8d...c8298`と一致した。
- `llama-server`はMach-O 64-bit x86_64だった。
- runtime versionは`9637 (aedb2a5e9)`だった。
- compiler表示は`AppleClang 17.0.0.17000013 for Darwin x86_64`だった。
- `--list-devices`は`BLAS: Accelerate`のみを列挙した。
- 公式x86_64配布物ではMetalを利用しないため、Phase 1のCPU-only環境基準として採用する。

## 切り分け上の意味

MoE側は既製の公式binaryをそのまま使い、ローカルでbuildする対象をHEADだけに限定できる。今後Metal版llama.cppが必要になった場合は別工程でlocal buildし、このbaselineへ混ぜない。

## 次の工程

`Granite 4.0 H-Tiny Q4_K_M`の公式file名、size、SHA256を固定し、weight取得後にhashを検証する。一般応答や負荷試験はmodel取得結果をremoteへ保存してから開始する。
