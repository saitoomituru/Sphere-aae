# 実機テストノート

このディレクトリには、ローカル実機で行った再現可能なテストの計画、入力、結果、温度・資源ログ、判定を保存する。

運用規則:

- CPU/GPU負荷を掛ける前に、対象コードと計画をcommitしてremoteへpushする。
- runごとに独立したUTC timestampのディレクトリを作る。
- runtime version、model SHA256、起動引数、Git commit、入力、出力を残す。
- Serial Number、Hardware UUID、token、絶対pathなど公開不要な情報はcommit前に除去する。
- 失敗結果も原因切り分けに必要な範囲で保存する。
- 実装・commit message・reportは、固有名詞やCLI optionを除いて可能な限り日本語で書く。
- 各段階の結果をcommit・pushしてから次の負荷段階へ進む。

進行中:

- [MoE HEAD baseline](moe-head-baseline/README.md)
