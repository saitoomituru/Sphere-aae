# Core ML最小ビルド実測レポート

- Git commit: `e7a4e7281f6d1c6ac228d2fd0b5c2f128a9f0591`
- 総合結果: **PASS**
- Thermal guard: 75 °C
- Thermal abort: なし
- GPU温度: 53–54 °C
- GPU activity: 2–8 %
- GPU power: 19–21 W
- GPU fan: 812–816 RPM
- GPU recovery count: 0–0
- Telemetry samples: 4 (4 profiles; short-run snapshots)
- CPU温度: CLIから取得できないため未記録

## Apple演算stack

- Core ML compute devices: CPU, GPU: AMD Radeon RX 5500 XT
- Metal device: AMD Radeon RX 5500 XT
- Metal 3: yes
- MPS: PASS
- Accelerate/vDSP: PASS

## Core ML結果

| profile | compute units | batch | iterations | max abs error | p50 ms | p95 ms | PASS |
|---|---|---:|---:|---:|---:|---:|---|
| latency | cpuAndGPU | 1 | 200 | 0.00000007 | 0.2189 | 0.3357 | yes |
| latency | cpuOnly | 1 | 200 | 0.00000007 | 0.1970 | 0.3140 | yes |
| throughput | cpuAndGPU | 256 | 50 | 0.00000025 | 0.3160 | 2.0432 | yes |
| throughput | cpuOnly | 256 | 50 | 0.00000025 | 0.1898 | 0.2952 | yes |

## 注記

- FAM信号、router replay、実weight MoEは未接続。
- `cpuAndGPU`はGPU使用を許可する指定であり、全operationのGPU配置を保証しない。
- GPU温度・電力・fanはAMD driverのIORegistry `PerformanceStatistics`から取得。
- このレポートのPASSを確認した地点で一旦停止し、FAM結合は別工程とする。
