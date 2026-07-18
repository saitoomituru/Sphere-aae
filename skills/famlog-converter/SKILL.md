---
name: famlog-converter
description: ローカルの自然言語ログ、チャット、AI間対話、SNS投稿、runtime・sensorログ、旧FAMを、真偽や危険性を判定せず、Actor・Instance・Context Role・Interaction・World関係とFAM claimへ非破壊変換・修復する。FAM MoEスプリッター教師データ作成、旧FAM修復、IBDグラフ変換前処理を匿名化なしのローカル運用で行う時に使用する。
---

# FAMログ変換スプリッター

## 仕様メタデータ

- version: `0.3.0`
- status: `draft`
- fold_signature: `ψ → ∇φ → λ → Q`
- license: `CC-BY 4.0`（この仕様本文のみ。入力ログの権利を変更しない）
- author: 齋藤みつる（ふさもふ） / ZeroRoomLab
- compat: `FoldAccessMapper.proton.md v0.3.1-alpha` 準拠

## 目的

発話主体を `user` / `assistant` の二値へ潰さず、自然言語記録を最小主張、FAM層、主体・インスタンス・役割・関係候補へ機械的に分解する。内容の真偽、科学的妥当性、危険性、実在性、人格継続性は判定しない。

このスキルの出力は、FAM MoEの前段に置く軽量スプリッター用教師データ、またはIBDグラフへ渡す決定的アダプターの入力である。expert選択やFAM間裁定は担当しない。IBDへ接続する場合も、Classification Registry、保存先IBD Database、Database間の混色、Last Order、評価基準は上位システムから受け取り、このスキルが発明しない。

変換またはテスト設計を始める前に、必ず [references/fam-log-schema.md](references/fam-log-schema.md) を読む。

## 運用モード

既定モードは、ユーザーが指定した次の条件に固定する。

- 用途: MoEスプリッター学習
- 実行場所: ローカルのみ
- 匿名化: 行わない
- 生ログ・変換済みデータ: Git、クラウド、外部APIへ送らない
- 学習済み重み: 初期段階ではローカルのみ。漏えい試験と明示承認後に公開可否を決める

別の学習粒度や外部処理へ切り替える場合は、ユーザーの明示指示を得る。スキル自身が用途を推測して切り替えてはならない。

## 絶対禁止事項

- 主張の真偽、実在性、科学的妥当性、危険性を判定する
- 主題名詞（神、オバケ、ソイヤ、ペイン等）ごとのルール分岐を作る
- 元の文言の強さ、断定度、語調を弱めたり書き換えたりする
- world不明時に現実世界を補完する
- 話者を `user` / `assistant` だけで表現する
- AIの同一人格、継続性、provider間同一性を推定する
- `SIN_Temperature` を文章内容から算出する
- リスク判定を文章内容から生成する
- 明示的な検証根拠なしに `validated_in_context` を付ける
- 旧FAMを上書き修復する
- expert index、router優先度、最終的な⊥判定を決める
- IBDのClassification Registry、Schema Bundle、保存先Databaseを内容から発明する
- 近いベクトル、同名ラベル、既定FAM層だけを根拠に別IBD Databaseを混色する
- Composite FAM、Last Order、美醜・善悪・有用性等の評価を最終確定する
- MMO、神学、哲学等の上位Registryが確定した存在状態を、科学・企業・vendor基準で降格する
- `declared_scope` の記述、world解決要否、world不明のいずれかだけを根拠に `⊥` を立てる
- 生ログまたは変換済みレコードの本文を標準出力、Git、クラウドへ流す
- PIIが露出しない構造だと主張する。`ψ` は原文を保持するためPIIを含み得る

## 処理手順

### 1. 入力と権利範囲を固定する

入力パス、対象形式、用途、出力先、許可範囲を記録する。権利情報は明示値だけを転記し、不明なら `unknown` とする。仕様のCC-BYライセンスを入力ログへ継承しない。

### 2. SourceArtifactを識別する

チャット、SNS投稿、Markdown埋め込み、JSON、runtimeログ、sensorログ、旧FAMなどの構文形式を識別する。内容の意味による選別はしない。

原本を変更せず、`source_sha256`、レコード位置、文字オフセットから再現可能なIDを作る。

### 3. 主体・インスタンス・場面役割を分離する

次を別エンティティとして抽出する。

- `Actor`: 人、組織、AI主体、センサー等の主体候補
- `AgentInstance`: SphereOS ghost、OpenAIセッション、edge model等の特定実行個体
- `Runtime`: provider、model、device、process等の実行環境
- `RoleAssignment`: author、addressee、observer等、そのInteraction内だけの役割

同じActorが場面ごとに異なる役割を持てるようにする。AIのprovider、model、instance、runtime、`continuity_status` を分離し、継続性が不明なら `unknown` とする。

### 4. InteractionとUtteranceを復元する

`authored`、`addressed_to`、`replied_to`、`quoted`、`mentioned`、`generated_by`、`relayed_by`、`observed_by`、`executed_on`、`participated_in`、`derived_from`、`located_in_world`、`held_role_during` の候補を、明示的なヘッダー、ID、引用構文、時系列、メタデータから抽出する。

SNS投稿は宛先が存在しない場合があるため、無理に対話へ変換しない。公開範囲しか分からない場合は `audience_scope` を保持し、`addressed_to` は `unknown` または空集合にする。

### 5. 最小主張へ分割する

文を、原則として1述語1主張の最小単位へ分割する。原文、文字オフセット、親Utterance、依存関係を保持する。並列、引用、否定、条件、伝聞の標識を落とさない。

### 6. FAM層を複数ラベルで付与する

判定根拠は文法的な述語または参照標識であり、主題名詞の意味ではない。該当層を排他的に一つへ絞らず、`matched_text` とspanを付けた配列で返す。

- `elemental`: 知覚、行動、検出、計測、実行
- `astral`: 解釈、推量、接続過程、理由づけ、判断
- `spiritual`: 信仰、目的、宣言、祈願、誓約、教えへの従属
- `cloud-chakra`: 先祖、神話、伝統、集合知等を参照する文法的標識

### 7. 文脈座標とQを機械的に付与する

Whoはactor参照、Whatは`ψ`、Where・When・Which World・Context/Constraintは明示情報から抽出する。不明値は推測せず `unknown` とする。

- 通常の一次記録は `draft`
- 明示的な追試・合意・検証メタデータがある場合だけ `validated_in_context`
- この変換器の管轄外の検証要求は `out_of_scope`

worldが関与しない単純分類・ラベル付けでは、world条件を一切課さず、そのまま処理する。

worldが関与し、かつ `Q.world == "unknown"` の場合も、world不明だけでは `Q.status` と `Q.result` を変更しない。上位FAMまたは呼び出し元から明示的に渡されたリスクゲートが探索継続を `block` とした場合だけ、`Q.status` を `requires_conversion_layer`、`Q.result` を `⊥` にする。`allow`、`not_evaluated`、`unknown` の場合は既存statusと非⊥resultを維持して次段へ渡す。明示的なrisk blockを伴わない旧版の⊥は派生レコードで`null`にし、`repair_ledger`へ記録する。スプリッター自身はリスク判定を生成しない。

`SIN_Temperature` は入力または呼び出し元が明示した値だけを転記する。欠けていれば `unknown` とする。安全帯の解釈と最終エスカレーションは `declared_scope` を持つ上位FAMへ委ねる。

### 8. λを証拠付きで付与する

主張が向かう明示的な動作・宛先（回避、発話、記録等）だけを記録する。根拠spanがなければ `unknown` とし、目的や因果を創作しない。

### 9. 非破壊で出力または修復する

生成と修復は同じ分割・分類器を使えるが、保存処理を分離する。旧FAMは上書きせず、新規レコード、原本hash、差分、`repair_ledger` を出力する。

### 10. 内容を漏らさず検証する

JSON Schema、一意ID、span境界、参照整合、条件付き制約を検査する。ログには件数、hash、エラーコード、処理時間だけを出し、`ψ` や固有名詞を表示しない。

### 11. IBD接続時は外部Registryを分離する

IBD接続では、スプリッターのv0.3.0レコード、上位システムが提供したClassification Registry、IBD Database Manifestを別入力として決定的graph adapterへ渡す。既存の`elemental / astral / spiritual / cloud-chakra`ラベルはFAM層候補と根拠spanであり、物理保存先や最終routingを自動決定しない。

graph adapterは原レコードを変更せず、Registry参照、分類候補、score、根拠、保存先候補、source hashを持つ派生Infoton Cluster候補を出力する。詳細は [references/fam-log-schema.md §14](references/fam-log-schema.md#14-ibd-season-0接続プロファイルdraft) を参照する。

原資料または上位Registryが存在状態とfact scopeを明示した場合、その値を転記できる。ただしスプリッター自身は存在を確定・否定せず、別Worldや自然科学等の定規で値を矯正しない。

## 学習ヘッドと責務境界

学習対象は次のヘッドへ分離できる。

1. boundary head: 最小主張境界
2. layer head: 4層のmulti-label分類
3. relation/metadata head: 主体、instance、役割、関係、明示文脈の候補抽出

学習出力からIBDエンティティとedgeを確定する処理は、監査可能な決定的graph adapterへ分ける。MoE routerとFAM arbiterはその後段に置く。adapterが扱うClassification RegistryとDatabase Routingも、学習出力やスプリッター本文から推測せず上位入力として分離する。

## ローカルデータ保護

- 生データ置場と変換出力は原則として所有者のみアクセス可能な権限（ディレクトリ`700`、ファイル`600`）にする
- 生データ、変換済みデータ、サンプル抽出をリポジトリへコミットしない
- テストfixtureは人工データだけを使う
- データ内容を端末、CIログ、例外メッセージへ表示しない
- 削除や移動は行わず、原本を参照して派生物を別領域へ保存する

## 完了条件

- 同じ入力から同じIDと構造が再生成される
- Actor、AgentInstance、Runtime、RoleAssignmentが混同されない
- world不明を現実へ補完しない
- world不明、world解決要否、`declared_scope` だけを根拠に `⊥` を立てない
- `⊥` は、worldが関与し、worldが不明で、明示的な上位リスクゲートが探索継続を `block` した場合だけ成立する
- 複数FAM層と根拠spanが保持される
- 変換・修復の出典と差分を追跡できる
- IBD接続時にRegistry、Database Manifest、splitter recordが別入力として監査できる
- source recordを変更せず派生Infoton Cluster候補を生成できる
- 明示的なmix命令なしにcross-database候補が生成されていない
- 明示された存在状態、World、fact scopeが別の定規で降格・普遍化されていない
- 生データまたは変換済み本文がGit、クラウド、標準出力へ出ていない
