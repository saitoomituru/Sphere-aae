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
5. CPU-only、context 2,048、temperature 0、生成・batchともにthread 6で短い日本語会話を実行する。
6. 一般応答、複数turn、tool call形式を確認する。
7. 応答、load時間、token速度、RSS、GPU telemetryをrun noteへ保存する。

実行command:

```bash
scripts/moe-head-baseline/run_upstream_baseline.sh
```

実行前checkはfail-closedとし、次のいずれかを満たさない場合はmodelをloadしない。

- branchが`moe-test-edition`で、作業treeがcleanである。
- `HEAD`がlocal upstreamと`origin`のlive remote SHAの両方に一致する。
- 空き容量が40 GiB以上ある。
- 固定runtime archive、`llama-server`、modelのSHA256が一致する。
- runtimeがx86_64かつAccelerate CPU-onlyである。
- AMD GPU温度telemetryを取得でき、実行開始時に75 °C未満である。
- `127.0.0.1:18080`を確保できる。

試験中はAMD GPU温度guardと`llama-server`のCPU/RSS監視を並走させる。CPU温度は非root CLIから直接取得できないため、physical core数と同じ6 threadへ制限し、load average、timeout、SIGTERMを併用する。会話応答は各case終了時に`note/`へ即時保存し、停電や熱停止時にも完了済みcaseを残す。

会話caseは、短い日本語応答、複数turn履歴、単一の合成tool callの3件とする。toolは構造だけを検証し、実際には実行しない。

固定runtime:

- release: `b9637` (`aedb2a5`)
- artifact: `llama-b9637-bin-macos-x64.tar.gz`
- SHA256: `71743f8db0958e7c266cceb7add7b16aa418a964667e471094aa6ae65b9c8298`
- 取得元: https://github.com/ggml-org/llama.cpp/releases/tag/b9637
- 注意: 公式macOS x86_64配布物はMetal無効。Phase 1のCPU-only基準に使い、Metal版は必要になった段階でlocal buildへ分離する。

固定model:

- repository: `ibm-granite/granite-4.0-h-tiny-GGUF`
- revision: `08d5a8a9741dd5c1a95d2d39e25253226aa1464e`
- file: `granite-4.0-h-tiny-Q4_K_M.gguf`
- size: `4,230,976,352 bytes`（約3.94 GiB）
- LFS SHA256: `5a38b08c441ae1adbafb1d2b8a7167e0d48734d83af68b268cefea1eec553dcd`
- 取得元: https://huggingface.co/ibm-granite/granite-4.0-h-tiny-GGUF/tree/08d5a8a9741dd5c1a95d2d39e25253226aa1464e

## Phase 2: MoE HEAD bypass baseline

1. 既存Core ML `16 -> 32 -> 4` fixtureをFAM未接続HEADとしてbuildする。
2. 入力はzero固定とし、FAM encodeを実装しない。
3. HEADのlogitsとdeterministic top-2をJSONへ記録する。
4. `router_override_applied=false`を機械可読に記録する。
5. HEADを実行してからPhase 1と同じpromptを実行する。
6. HEADが既存router、prompt、expert index、weightへ介入していないことを確認する。
7. crash、NaN、Inf、load failureがないことを確認する。

HEADはSwift packageの独立product `moe-head-baseline`として実装する。このtargetのpackage dependencyは空で、ML関連として明示linkするframeworkは`CoreML`だけである。`Foundation`以外のSphere-aae本体、MoE router、network clientには依存しない。実行時も`cpuOnly`固定で2回推論し、次をJSONへ保存する。

- `head_mode=observe_only`
- `fam_enabled=false`
- `input_mode=zero`
- `router_override_applied=false`
- actual / expected logits
- actual / expected top-2
- repeat一致、finite、shape、誤差、総合判定

HEAD実行前後の会話比較は同じ`llama-server` process、同一prompt、temperature 0、固定seed、prompt cache無効で行う。まずHEAD実行前のA1/A2一致で上流決定性を確認し、HEADを別processで実行した後のBがA1と一致することを確認する。

実行command:

```bash
scripts/moe-head-baseline/run_head_bypass_baseline.sh
```

fixture生成、`coremlcompiler`、Swift build、llama-serverの4区間を個別に温度監視する。各build区間の生出力、HEAD logits/top-2、A1/A2/B response、GPU telemetry、server CPU/RSS、artifact SHA256を同じrun noteへ保存する。

## PASS条件

- 公式runtime/modelだけで、日本語の一般応答が完走する。
- local HEADがbuild、Core ML compile、load、推論を完走する。
- HEAD出力が有限値で、top-2が決定的である。
- `router_override_applied=false`である。
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

## 実測状況

- Phase 1: **PASS** — [2026-07-14 上流MoE一般応答baseline](runs/20260714T044420Z-upstream-chat-p92737/REPORT.md)
- 一般日本語応答、複数turn履歴、合成tool callの3 caseが完走した。
- 実測は最大CPU 368.9 %、最大RSS 7,562.1 MiB、GPU温度53–54 °C、GPU recovery増分0だった。
- この結果をremoteへ保存してから、Phase 2のFAM未接続HEAD bypassへ進む。
