# Core ML実機ログ

このディレクトリには、`moe-test-edition`で実行したFAM非接続Core ML smoke testの実機ログとレポートを保存します。

実行前条件:

- 作業ツリーがcleanであること
- `HEAD`がupstreamへpush済みであること
- RX 5500 XTの温度telemetryが取得できること

実行:

```bash
scripts/coreml/run_smoke.sh
```

既定のthermal guardは80 °Cです。変更する場合:

```bash
COREML_MAX_GPU_TEMP_C=75 scripts/coreml/run_smoke.sh
```

各runは`logs/coreml/runs/<UTC timestamp>/`へ保存します。CPU温度はこのHackintoshで利用可能な非root CLIから取得できないため、現時点ではGPU温度・GPU activity・GPU power・fan・VRAM・GPU recovery countを記録します。

FAM、router replay、実weight MoEはこの試験へ接続しません。最小buildの見通しが立った時点で停止し、FAM結合は別工程で開始します。
