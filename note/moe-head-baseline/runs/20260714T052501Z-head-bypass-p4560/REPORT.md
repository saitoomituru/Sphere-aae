# MoE HEAD bypass baseline実測レポート

- 実行基盤: X99ベースのx86_64 Hackintosh（Apple純正Macではない）
- macOS提示identity: `MacPro7,1`（SMBIOS互換identity）
- Git commit: `f9ebdf19a0937aa0baea71fd629829e1201ecbfd`
- 総合結果: **PASS**
- 対象: 上流MoE一般応答 + local Core ML HEAD（FAM未接続）
- HEAD mode: `observe_only`
- HEAD input: `zero`
- router override: なし
- MoE応答へのHEAD出力注入: なし
- Thermal guard: 75 °C

## 工程status

| 工程 | exit status | 判定 |
|---|---:|---|
| fixture生成 | 0 | PASS |
| fixture thermal guard | 0 | PASS |
| coremlcompiler | 0 | PASS |
| compiler thermal guard | 0 | PASS |
| Swift HEAD build | 0 | PASS |
| Swift build thermal guard | 0 | PASS |
| A/B比較 | 0 | PASS |
| server thermal guard | 0 | PASS |
| server process監視 | 0 | PASS |
| server停止後 | 0 | PASS |

## HEAD安全条件

| 条件 | 値 | 判定 |
|---|---|---|
| FAM無効 | `False` | PASS |
| zero input | `zero` / all-zero=`True` | PASS |
| observe-only | `observe_only` | PASS |
| router override無効 | `False` | PASS |
| finite logits | max abs error=`3.725290298461914e-09` | PASS |
| output shape一致 | `[1, 4]` | PASS |
| stable top-k一致 | `[3, 2]` | PASS |
| repeat一致 | max abs error=`0` | PASS |

## A1 / A2 / HEAD / B比較

- A1=A2: PASS
- A1=B: PASS
- A2=B: PASS
- canonical message SHA256一致: PASS
- HEAD subprocess exit: `0`

| 応答 | canonical message SHA256 |
|---|---|
| A1 | `a8cf53e4d013e02e13c9c445e95951d3ee36621af10938024a8316fab11d9fce` |
| A2 | `a8cf53e4d013e02e13c9c445e95951d3ee36621af10938024a8316fab11d9fce` |
| B | `a8cf53e4d013e02e13c9c445e95951d3ee36621af10938024a8316fab11d9fce` |

## 成果物identity

- compiled model: `build/moe-head-baseline/head-runs/20260714T052501Z-head-bypass-p4560/compiled/MinimalArbiterZeroB1.mlmodelc`
- compiled model tree SHA256: `344042abfb65b5d4a197e01a949f3fe186c64e230610f581610441039eed3134`
- compiled model files: 5
- HEAD binary: `build/moe-head-baseline/head-swift/x86_64-apple-macosx/release/moe-head-baseline`
- HEAD binary SHA256: `b72289e53fb696d3bd7b59262a93c5763a1f9b50c420b582f80182617c09d43c`

## GPU telemetry

- 記録file数: 4（最低4系統）
- 有効sample数: 38
- 全区間recovery増分: 0.0
- CPU温度: 非root CLIから取得できないため未記録

| file | samples | GPU温度 | recovery増分 | abort | 判定 |
|---|---:|---|---:|---|---|
| telemetry-gpu-build-fixture.jsonl | 2 | 56.0–56.0 °C | 0.0 | なし | PASS |
| telemetry-gpu-compile-model.jsonl | 1 | 56.0–56.0 °C | 0.0 | なし | PASS |
| telemetry-gpu-server.jsonl | 21 | 57.0–59.0 °C | 0.0 | なし | PASS |
| telemetry-gpu-swift-build.jsonl | 14 | 56.0–57.0 °C | 0.0 | なし | PASS |

## llama-server監視と停止

- process samples: 27
- 最大CPU使用率: 460.1 %
- 最大RSS: 7317.3 MiB
- process telemetry: PASS
- runnerからのSIGTERM要求: あり
- server強制SIGKILL: なし
- 通常停止判定: PASS

## 判定

- 全必須条件を満たしたためPASS。

## 停止点

- このrunではFAM encode、FAM優先順位規則、router replay注入を実装・実行していない。
- HEADはzero inputの出力を観測しただけで、上流MoE応答へ一切反映していない。
- PASS/FAILを問わず本工程で停止し、FAM algorithm調整は別承認後に行う。
