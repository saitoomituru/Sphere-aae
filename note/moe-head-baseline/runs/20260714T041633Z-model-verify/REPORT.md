# Granite固定model検証結果

- 実行日時: 2026-07-14 04:16:33 UTC
- 判定: **PASS**
- 対象Git commit: `73d223887e7b024b55632fce4077df35c438acbc`

## 確認結果

- IBM公式repositoryの固定revisionから`granite-4.0-h-tiny-Q4_K_M.gguf`を取得した。
- file sizeは`4,230,976,352 bytes`で公式値と一致した。
- SHA256は`5a38b08c441ae1adbafb1d2b8a7167e0d48734d83af68b268cefea1eec553dcd`で公式LFS値と一致した。
- 取得後のdisk空き容量は約64 GiBで、40 GiB停止線を上回っている。
- model fileは`build/`配下に置き、Git管理対象へ含めていない。

## 未実施

- model load
- token生成
- 一般応答
- HEAD build / run
- FAM入力とrouter override

## 次の工程

上流MoE一般応答runnerと固定prompt fixtureを追加し、remoteへpushした後に初回model loadを行う。CPU-only、6 thread、context 2,048、temperature 0、75 °C guardを初期条件とする。
