# 扁桃体MoE裁定器: 訓練手法と裁定思想の補足調査

- 作成: Fable5 (buddy researcher、コード・テスト・実行ログには一切触れていない)
- 作成日: 2026-07-14 (JST)
- 位置づけ: [`docs/development/coreml-moe-test-plan.md`](../../docs/development/coreml-moe-test-plan.md) と
  [`docs/development/moe-test-stack-research.md`](../../docs/development/moe-test-stack-research.md) を横から読んだ上での補足デスクリサーチ。
  実装・テストケース・`note/moe-head-baseline/`配下の実行記録はSolの担当領域のため変更していない。新規ファイルのみ追加。
- 範囲: (1) router自体の訓練手法、(2) 複数信号同時到着の裁定という設計思想の先例、(3) Core ML MIL演算子の在庫確認。
  実装判断や採否はしていない。

## 1. まだ埋まっていない穴: `router_replay`は推論時の差し替えであって訓練ではない

`moe-test-stack-research.md` はPithTrain PR #62の`router_replay`契約を精査済みだが、これは**推論時にexpert indexを外部から上書きするhook**であり、
README §193-206が本来目指す「frozen experts + 軽量trainable router/adapter」の**router訓練そのもの**とは別の問題である。
Core MLアービターの重みを最終的にどう学習させるかは、現状どちらの文書にもまだ書かれていない。

2026年前半の関連研究を確認すると、frozen expertsを前提にrouterだけを学習させる手法は概ね3系統に分かれる。

### 系統A: 教師モデルからのrouter蒸留

- **GRouter**（[arXiv:2603.06626](https://arxiv.org/html/2603.06626v2)）— 収束済みモデルから高品質なrouting決定を軽量な独立networkへ蒸留し、
  router-expert同時最適化の不安定性を排除する。expert folding / expanding / tuningと組み合わせ、単一の蒸留済みGRouterインスタンスが
  異なるモデル規模・expert構成へ流用できると報告。throughput +33.5%。
- **TGR-MoE**（Teacher-Guided Routing、[arXiv:2604.21330](https://arxiv.org/html/2604.21330v1)）— frozenの教師backboneにauxiliary router を付け、
  KLダイバージェンスでstudent routerへ分布を蒸留する構成。vision MoE向けだが、教師出力を裁定の正解ラベルとして使う発想はFAM信号裁定にも転用しやすい。
- **Router Knowledge Distillation** — モデル全体を凍結し、routerパラメータだけをcalibrationデータ上のnext-token分布蒸留で更新する軽量手法。

### 系統B: frozen expert adapter + 別訓練router（前回セッションで確認済み、再掲）

- **TT-LoRA MoE**（[arXiv:2504.21190](https://arxiv.org/pdf/2504.21190)、実装 [lanl/TTLoRAMoE](https://github.com/lanl/TTLoRAMoE)）—
  各task用のtensor-trained低rank adapterを個別に訓練・凍結した後、base modelとexpert双方を凍結したままsparse routerだけを別訓練する二段階構成。
  ただし実装は2025-05以降pushが止まっており、参照実装としては有用だが追従先には向かない（前回セッションで確認済みの評価を維持）。

### 系統C: 教師なしの直接勾配（比較対象として）

- 標準的なMoE(Switch Transformer系)のjoint training。frozen experts前提のSphere-aae扁桃体MoEには非該当だが、
  「なぜjoint trainingを避けてfrozen expert前提にするか」の対比としてGRouter論文内の不安定性の議論が参考になる。

**示唆**: Core MLアービター（16→32→4のFAM裁定器）を実weightで訓練する段階に進む場合、系統A（教師蒸留、特にGRouterの「収束済みroutingを固定した軽量networkへ移す」考え方）が、
`.venv-moe-reference`側でPyTorch実装→重みを`.npz`化→MILへ注入、という既存の移行経路と最も相性が良い。既存Qwen2MoE/Qwen3MoEのgate出力をteacher signalとして扱えば、
FAM裁定器訓練とexpert weight凍結を両立できる可能性がある。ただしこれは示唆に留め、実装判断はしていない。

## 2. 「複数信号の同時到着裁定」という設計思想の先例: Subsumption Architecture

`Sphere-aae/README.md` §191-206の扁桃体MoEは、「複数のFAM信号(アストラル階層/エレメンタル階層など)が同時に到着した場合の結合順序・優先順位の裁定」を目的とする。
これはMoEの語彙で語られているが、問題の構造自体はロボティクスのbehavior-based AIにおける**arbitration（裁定）機構**、
特にRodney Brooksのsubsumption architecture（[Wikipedia](https://en.wikipedia.org/wiki/Subsumption_architecture)）と同型である。

- Subsumption architectureでは、各層(behavior)が独立にactuator commandと「制御を取りたいか」を示すbinary信号を出力し、
  優先順位付けされたarbitration機構がsuppression（抑制）とinhibition（抑止）によって上位層が下位層を上書きする。
- 開発順序も「最下層を先に作って動かし、その後で上位層をsuppression/inhibition接続込みで足していく」というボトムアップ構成であり、
  Sphere-aaeの「T0〜T2はFAM非接続、T7で初めて既存gateへ接続」という段階的統合方針と構造的に一致する。
- **設計上の対応関係の仮説**: FAM信号の`⊥ LAST_ORDER`(接続不能の申告)は、Subsumption architectureの「下位層の出力を上位の緊急behaviorがsuppressする」構図に近い。
  扁桃体MoEを「複数のbehavior層が同時に制御を要求したときの優先順位裁定機構」として設計するなら、
  MoEのtop-kゲーティングよりもsuppression/inhibitionの二値的な上書きモデルの方が、FAMの「回復探索へ遷移すべきか」という判断に近い可能性がある。

これは実装を示唆するものではなく、「扁桃体MoEをMoEの語彙だけでなくarbitration architectureの語彙でも眺めておくと、
frozen expertsへの干渉を最小化しながら優先順位だけを裁定するという要件を、閾値付きsuppressionのような単純な仕組みで満たせないか」という
検討の切り口を増やす目的の資料。

## 3. Core ML MIL演算子の在庫確認（`coreml-moe-test-plan.md` §3への補足情報）

`coreml-moe-test-plan.md`は「Core ML内へtop-kを埋め込まない」という設計判断を明記しているが、理由は
「裁定器の浮動小数点誤差とindex契約の不具合を別々に検査するため」であり、**MILにtop-kが存在しないからではない**。
これを裏付ける在庫確認結果を残す。

[coremltools MIL Ops Reference](https://apple.github.io/coremltools/source/coremltools.converters.mil.mil.ops.defs.html)によると:

| 演算 | 対応 |
|---|---|
| `topk` | iOS15+で提供、iOS16+/iOS17+で改善版あり |
| `gather` / `gather_along_axis` / `gather_nd` | iOS15+、iOS16+、iOS17+いずれでも提供 |
| `scatter` / `scatter_along_axis` / `scatter_nd` | iOS15+、iOS17+で提供 |
| `argsort` | iOS15+で提供 |

したがって、T7以降で「Core ML内でtop-kまで完結させる」経路へ切り替える技術的余地は最初から存在する
（custom operatorの実装は不要）。現行計画の「top-kをhost側adapterに置く」判断は、
MILの制約ではなく**誤差切り分けのための意図的な設計**であることを裏付ける情報として記録しておく。

## 4. `mlc-ai/pith-train` issueトラッカーの確認

2026-07-14時点でopenのissueはPRを除き1件のみ。

- [#49 "Future plan about extending to post-train (RL/SFT/OPD)"](https://github.com/mlc-ai/pith-train/issues/49)（2026-06-03起票）—
  PithTrainをpost-training(RL/SFT/OPD)やauto-researchへ拡張する予定を尋ねる質問で、`router_replay`まわりの変更予定を示す情報はない。
  現行のCore MLアービター計画をブロックする要素は確認できなかった。

## 参照した一次資料

- GRouter: https://arxiv.org/html/2603.06626v2
- TGR-MoE: https://arxiv.org/html/2604.21330v1
- TT-LoRA MoE: https://arxiv.org/pdf/2504.21190 / https://github.com/lanl/TTLoRAMoE
- Subsumption architecture: https://en.wikipedia.org/wiki/Subsumption_architecture
- coremltools MIL Ops Reference: https://apple.github.io/coremltools/source/coremltools.converters.mil.mil.ops.defs.html
- pith-train issue #49: https://github.com/mlc-ai/pith-train/issues/49
