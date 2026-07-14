# 上流MoE一般応答baseline実測レポート

- Git commit: `dc5948906fb50f80bb25f224e0106ae6c85da95e`
- 総合結果: **PASS**
- 対象: IBM Granite 4.0 H-Tiny Q4_K_M + llama.cpp b9637 x86_64
- 演算経路: Accelerate CPU-only（Metal / GPU offloadなし）
- FAM接続: なし
- local HEAD接続: なし
- router override: なし
- Thermal guard: 75 °C
- Thermal abort: なし
- Telemetry abort: なし
- Telemetry完全性: PASS
- Process監視完全性: PASS
- GPU温度: 53.0–54.0 °C
- GPU activity: 1.0–8.0 %
- GPU power: 19.0–21.0 W
- GPU fan: 0.0–0.0 RPM
- GPU recovery増分: 0.0
- llama-server最大CPU使用率: 368.9 %
- llama-server最大RSS: 7562.1 MiB
- 最大1分load average: 5.75
- CPU温度: 非root CLIから取得できないため未記録

## 会話case

| case | 目的 | HTTP | 秒 | 判定 | 内容 |
|---|---|---:|---:|---|---|
| japanese_general | 短い日本語の一般応答 | 200 | 5.85 | PASS | 日本語応答あり |
| japanese_multi_turn | 会話履歴を使う複数turn応答 | 200 | 2.23 | PASS | 期待文字列『青い星』を確認 |
| synthetic_tool_call | 合成weather toolの呼び出し形式 | 200 | 5.82 | PASS | get_current_weather tool callを確認 |

## 実行status

- preflight: PASS
- chat runner exit: 0
- thermal guard exit: 0
- process monitor exit: 0
- server shutdown後status: 0（runnerのSIGTERM終了は異常扱いしない）
- runnerからのshutdown要求: あり
- server強制KILL: なし

## 判定と次工程

- このrunは上流runtime/modelだけの環境baselineであり、FAM algorithmとlocal HEADを一切実行していない。
- PASS時のみ、別commitでFAM未接続HEAD bypassのbuildへ進む。
- HEAD bypassがPASSしてもFAM encode、優先順位規則、router replay注入には着手せず停止する。
