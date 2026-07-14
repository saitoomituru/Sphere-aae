# MoE HEAD baseline実行計画

- 作成日: 2026-07-14 (JST)
- 対象branch: `moe-test-edition`
- 目的: FAM algorithmへ触れる前に、既製MoE runtime/modelとlocal HEADの環境健全性を分離して確認する
- 停止地点: HEAD bypass baselineのPASS。FAM encode、優先順位規則、router replay注入は実施しない

## 判定する境界

```text
公式MoE runtime + 公式GGUF
  -> 一般応答baseline
  -> local HEADをbuild/load/run
  -> HEAD override=falseで同一応答を再確認
  -> 停止

ここから先は別工程:
  固定FAM fixture
  -> top-k adapter
  -> router replay
  -> 実FAM
```

## Phase 1: 上流MoE一般応答baseline

1. 公式llama.cpp `b9637` macOS x86_64 runtimeをversion固定で取得する。
2. 配布物のhash、version、取得元をmanifestへ保存する。
3. `Granite 4.0 H-Tiny Q4_K_M`を公式repositoryから取得する。
4. model SHA256とsizeをmanifestへ保存する。
5. CPU-only、context 2,048、temperature 0、thread 6で短い日本語会話を実行する。
6. 一般応答、複数turn、tool call形式を確認する。
7. 応答、load時間、token速度、RSS、GPU telemetryをrun noteへ保存する。

固定runtime:

- release: `b9637` (`aedb2a5`)
- artifact: `llama-b9637-bin-macos-x64.tar.gz`
- SHA256: `71743f8db0958e7c266cceb7add7b16aa418a964667e471094aa6ae65b9c8298`
- 取得元: https://github.com/ggml-org/llama.cpp/releases/tag/b9637
- 注意: 公式macOS x86_64配布物はMetal無効。Phase 1のCPU-only基準に使い、Metal版は必要になった段階でlocal buildへ分離する。

## Phase 2: MoE HEAD bypass baseline

1. 既存Core ML `16 -> 32 -> 4` fixtureをFAM未接続HEADとしてbuildする。
2. 入力はzeroまたは固定vectorとし、FAM encodeを実装しない。
3. HEADのlogitsとdeterministic top-2をJSONへ記録する。
4. `override_applied=false`を機械可読に記録する。
5. HEADを実行してからPhase 1と同じpromptを実行する。
6. HEADが既存router、prompt、expert index、weightへ介入していないことを確認する。
7. crash、NaN、Inf、load failureがないことを確認する。

## PASS条件

- 公式runtime/modelだけで、日本語の一般応答が完走する。
- local HEADがbuild、Core ML compile、load、推論を完走する。
- HEAD出力が有限値で、top-2が決定的である。
- `override_applied=false`である。
- HEAD前後の決定的prompt応答が一致する。
- thermal abortとGPU recoveryがない。
- 作業ツリーとremoteの同期を各負荷試験前に確認できる。

## FAILの帰属

| 失敗地点 | 主な帰属 |
|---|---|
| runtime起動前 | binary、macOS、署名、architecture |
| model load | GGUF、RAM、runtime architecture対応 |
| HEAD build/load | Core ML toolchain、HEAD artifact、Swift結合 |
| HEAD bypass前後の差 | orchestration、prompt、seed、HEAD介入漏れ |
| FAM接続後だけ失敗 | この計画の範囲外。FAM / adapter / router契約 |

## 保存場所

- download artifact: `build/moe-head-baseline/`（Git管理外）
- 実行結果: `note/moe-head-baseline/runs/<UTC timestamp>/`
- runtime/model manifest: 各run directoryの`manifest.json`
- 総括: 各run directoryの`REPORT.md`

## commit checkpoint

1. この計画と保存規則
2. runtime取得・検証scriptとruntime manifest
3. model取得・hash確認結果
4. 上流一般応答baseline結果
5. HEAD bypass実装
6. HEAD bypass baseline結果

各checkpointを`origin/moe-test-edition`へpushしてから次へ進む。
