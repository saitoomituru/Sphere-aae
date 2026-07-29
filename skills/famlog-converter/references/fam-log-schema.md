# FAMログ・スプリッター構造契約 v0.3.0

この文書は `famlog-converter` の詳細な入出力契約である。実装、変換、教師データ設計、fixture作成の前に参照する。

## 目次

1. 責務境界
2. エンティティ
3. 関係候補
4. 推奨レコード形
5. FAM層ルーティング
6. Q.statusの機械的決定
7. SIN_Temperature
8. Actor・Instance・Runtime
9. 安定ID
10. 非破壊修復
11. 教師データのヘッド分離
12. データ保護とGit
13. 検証項目
14. IBD Season 0接続プロファイル
15. Context Dimension／OAE candidate sidecar

## 1. 責務境界

スプリッターが担当するもの:

- claim境界の抽出
- FAM層のmulti-label分類と根拠span
- Actor、AgentInstance、Runtime、RoleAssignment候補
- author、addressee、quote、mention等の関係候補
- 明示されたWorld、Where、When、Contextの抽出
- 出典、hash、span、変換器versionの監査情報

担当しないもの:

- 真偽、実在性、危険性、科学的妥当性の判定
- 人格・AI instanceの同一性判定
- worldの推測
- SIN値の生成
- expert選択、優先順位裁定、最終的な⊥への格上げ
- 法的権利や学習許可の推定

## 2. エンティティ

| 型 | 意味 |
|---|---|
| `SourceArtifact` | ファイル、投稿、export、ログ等の原資料 |
| `Interaction` | 会話、スレッド、セッション、観測場面 |
| `Actor` | 人、組織、AI主体、sensor等の主体候補 |
| `AgentInstance` | 特定セッション、ghost、edge process等の実行個体 |
| `Runtime` | provider、model、device、process、version |
| `RoleAssignment` | Interaction内でのauthor、addressee、observer等 |
| `Utterance` | 一つの発話、投稿、event payload |
| `Claim` | 1述語を原則とする最小主張 |
| `World` | 現実物理、ゲーム、TRPG、2.5D空間等。未確定可 |

`actor_kind`の既存enumはsource format上の粗い候補分類であり、Agency存在論の共通正本ではない。神、動物、自然現象、World等をこのenumへ追加して平板化せず、上位Registry付き`agency_kind_ref`をsidecarで扱う。

## 3. 関係候補

次のedge名を基本語彙とする。

`authored`, `addressed_to`, `replied_to`, `quoted`, `mentioned`, `generated_by`, `relayed_by`, `observed_by`, `executed_on`, `participated_in`, `derived_from`, `located_in_world`, `held_role_during`

edgeには必ず `evidence_span` または構造メタデータ由来の `evidence_ref` と、`source_kind` を付ける。推測だけのedgeは確定せずcandidateとして扱う。

## 4. 推奨レコード形

```json
{
  "schema_version": "fam.log.splitter/0.3.0",
  "record_id": "famrec:sha256-prefix:interaction-0001:claim-0003",
  "source": {
    "source_artifact_id": "source:sha256-prefix",
    "source_sha256": "hex",
    "source_record_id": "provider-or-local-record-id-or-unknown",
    "artifact_kind": "chat|social_post|markdown|json|runtime_log|sensor_log|legacy_fam|unknown",
    "rights_scope": "explicit-value-or-unknown",
    "training_allowed": "true|false|unknown",
    "export_allowed": "true|false|unknown"
  },
  "interaction": {
    "interaction_id": "interaction:sha256-prefix:0001",
    "interaction_kind": "dialogue|thread|broadcast|observation|runtime_event|unknown",
    "audience_scope": "public|private|group|unknown",
    "world_ref": "world:unknown"
  },
  "participants": [
    {
      "actor_id": "actor:source-local:0001",
      "display_label": "原資料の明示表記",
      "actor_kind": "human|organization|ai|sensor|service|unknown",
      "instance_ref": "instance:source-local:0001-or-null",
      "role_assignments": ["author"],
      "continuity_status": "explicit|unknown"
    }
  ],
  "utterance": {
    "utterance_id": "utterance:sha256-prefix:0007",
    "actor_ref": "actor:source-local:0001",
    "instance_ref": "instance:source-local:0001-or-null",
    "turn_id": "source-turn-id-or-derived-id",
    "source_span": {"start": 120, "end": 151},
    "text": "原文を変更せず保持"
  },
  "claim": {
    "node_id": "fam:node:sha256-prefix:0003",
    "parent_id": null,
    "depends_on": [],
    "ψ": "元の最小単位テキスト",
    "∇φ": [
      {
        "layer": "elemental",
        "matched_text": "検出した",
        "evidence_span": {"start": 5, "end": 9}
      }
    ],
    "λ": {
      "kind": "record|utter|avoid|execute|unknown",
      "target_ref": null,
      "matched_text": null,
      "evidence_span": null
    },
    "Q": {
      "status": "draft",
      "world": "unknown",
      "where": "unknown",
      "when": "unknown",
      "context": "unknown",
      "world_relevance": "not_involved",
      "risk_gate": {
        "decision": "not_evaluated",
        "source": "upstream-or-caller",
        "evidence_ref": null
      },
      "result": null,
      "source": {"SIN_Temperature": "unknown"},
      "declared_scope": "splitter_training"
    },
    "lifecycle_status": "draft"
  },
  "relations": [],
  "audit": {
    "converter": "famlog-converter",
    "converter_version": "0.3.0",
    "generated_at": "RFC3339 timestamp",
    "repair_applied": false,
    "repair_ledger_ref": null
  }
}
```

`Q.status` は文脈上の検証状態、`lifecycle_status` は変換レコード自体の編集状態であり、同義ではない。意味を分離して値の漂流を防ぐ。

## 5. FAM層ルーティング

| 層 | 文法的根拠 | 例 |
|---|---|---|
| `elemental` | 知覚・行動・検出・計測・実行述語 | 見た、聞いた、測った、逃げた、実行した |
| `astral` | 解釈・推量・接続過程・理由づけ・判断述語 | 思った、気がした、繋がった、判断した |
| `spiritual` | 信仰・目的・宣言・祈願・誓約述語 | 信じる、祈る、誓う、教えに従う |
| `cloud-chakra` | 集合知・伝統を参照する文法的標識 | 先祖が、神話では、伝統的に、古来より |

名詞が特定テーマを指すだけでは層を決めない。一つのclaimが複数条件を満たす場合、すべてのラベルを保持する。

`claim.∇φ[].layer`は`fam.log.splitter/0.3.0`の互換field名である。ここでの層は文法的なFAM label候補であり、技術依存のLayer `L`、上位Registryが宣言するContext Dimension `D`、embedding dimensionではない。

multi-label候補が四つ揃っても、自動的に4D Foldとはしない。D Foldは別のFold ManifestがID、revision、Dimension refsを宣言する。

## 6. Q.statusの機械的決定

| 値 | 必要条件 |
|---|---|
| `draft` | 一次記録または明示検証メタデータなし |
| `validated_in_context` | 原資料に追試、合意、sensor再観測等の検証メタデータが明示されている |
| `out_of_scope` | 呼び出し元が、この変換器の担当外にある形式検証を要求している |
| `requires_conversion_layer` | worldが関与し、worldが不明で、明示的な上位リスクゲートが探索継続を`block`した |

worldが関与しない処理（単純な分類・ラベル付け等）はworld判定の対象外とする。`Q.world`、`world_relevance`、`risk_gate`、`Q.result`へ追加条件を課さず、そのまま処理する。

worldが関与する処理では、次の不変条件を適用する。

```text
if world_relevance == "involved" and Q.world == "unknown":
    if risk_gate.decision == "block":
        Q.status = "requires_conversion_layer"
        Q.result = "⊥"
    else:
        Q.status = existing_Q_status
        Q.result = existing_Q_result if existing_Q_result != "⊥" else null
```

`risk_gate.decision` は上位FAMまたは呼び出し元が明示した `block|allow|not_evaluated|unknown` だけを転記する。スプリッターは文章内容からリスクを判定しない。

`⊥` が成立するのは、worldが関与し、worldが不明で、明示的なリスクゲートが `block` を返した場合だけである。`declared_scope` の記述、world resolution要否の明示、world不明のいずれかだけを根拠に `⊥` を立ててはならない。`allow|not_evaluated|unknown` ではstatusを維持し、resultも非⊥値なら維持して次段へ渡す。

v0.2系の入力に、明示的なrisk blockなしで `Q.result == "⊥"` が残っている場合、その⊥はv0.3.0の不変条件を満たさない。非破壊修復として派生レコード側を `null` にし、変更理由を`repair_ledger`へ記録する。原資料は変更しない。

## 7. SIN_Temperature

`SIN_Temperature` は次のいずれかだけを許す。

- 原資料に明示された値とそのspan
- 呼び出し元が `declared_scope` と共に渡した値
- `unknown`

文章内容から値を推定しない。0側・2側のどちらが安全かも決めない。用途別の安全帯、gestalt維持、リスクゲート、最終的な⊥判定は上位FAMの責務とする。

## 8. Actor・Instance・Runtime

`user` / `assistant` はsource format上の一時的roleとして保持してよいが、Actorの恒久種別にはしない。

AI系主体は最低限、次を独立fieldにする。

```json
{
  "actor_ref": "actor:...",
  "provider": "explicit-or-unknown",
  "model": "explicit-or-unknown",
  "instance_id": "explicit-or-derived-or-unknown",
  "runtime_ref": "runtime:...-or-null",
  "continuity_status": "explicit|claimed|unknown"
}
```

「同じスフィア」「別ghost」「OpenAI assistant」「edge model」等の記述は原文上のclaimまたはlabelとして保持する。変換器は同一性を確定しない。

## 9. 安定ID

IDは乱数ではなく、次の安定要素から決定的に生成する。

```text
source_artifact_id = sha256(canonical_source_bytes)
interaction_id     = hash(source_artifact_id + source_interaction_key)
utterance_id       = hash(interaction_id + turn_key + source_span)
claim_id           = hash(utterance_id + claim_source_span + splitter_version)
```

文字コード、改行、canonicalization方式を実装側で固定する。原本hashとcanonicalized hashを混同しない。

## 10. 非破壊修復

修復出力には最低限、次を含める。

```json
{
  "repair_ledger": {
    "input_sha256": "hex",
    "output_record_id": "famrec:...",
    "operations": [
      {
        "op": "add|replace|split|link",
        "path": "/json/pointer",
        "before_hash": "hex-or-null",
        "after_hash": "hex",
        "reason_code": "schema_migration|boundary_split|missing_reference|other"
      }
    ]
  }
}
```

原資料を変更しない。修復前後の本文をログへ表示しない。

## 11. 教師データのヘッド分離

| ヘッド | 目的 | 主な教師信号 |
|---|---|---|
| boundary head | claim境界 | span start/end、依存関係 |
| layer head | FAM層multi-label | layer配列、matched span |
| relation/metadata head | 主体と関係候補 | Actor/Instance/Role、edge、明示文脈span |

graph adapterは候補をIBD schemaへ写像する決定的処理にする。学習ヘッドへexpert routingや最終裁定を混ぜない。

## 12. データ保護とGit

- このスプリッター訓練では匿名化しない
- 固有名詞、関係、伝統・神話の出典を分類証拠として保持する
- ただし`ψ`とmetadataはPIIを含み得るため、出力そのものを機密データとして扱う
- 生ログと変換済みデータはローカル参照のみでGit対象外
- 重みも初期段階ではローカルのみ。membership inference、canary、固有名詞再生試験等を経て明示承認された成果物だけを公開候補にする
- CIとrepository fixtureには人工データだけを置く

## 13. 検証項目

- JSON Schema妥当性
- source spanがUTF-8またはUnicode scalarのどちらを数えるか統一されている
- IDが再実行で変化しない
- 全参照先が存在する、または明示的に`unknown`/`null`である
- layerに`matched_text`とspanがある
- `validated_in_context`に明示検証根拠がある
- world非関与の処理にworld条件が課されていない
- world関与かつunknownでも、明示的な`risk_gate.decision == "block"`でなければstatusとresultが変更されていない
- `result == "⊥"`なら、world関与・world unknown・明示的なrisk blockの3条件がすべて監査可能である
- repair時に原本が不変でledgerがある
- 標準出力、ログ、Git差分に実データ本文がない

## 14. IBD Season 0接続プロファイル（DRAFT）

この節は`fam.log.splitter/0.3.0`の出力Schemaを変更しない。既存splitter recordを、IBD Season 0のClassification Registry、Schema Bundle、IBD Database、Infoton Clusterへ接続する後段adapter契約を定める。

### 14.1 責務分離

```text
famlog-converter
  claim境界、FAM層候補、Actor／Instance／Runtime、根拠spanを抽出
        ↓
upper system
  Classification Registry、λ、Q、Database範囲、mix、評価規約を提供
        ↓
deterministic IBD graph adapter
  Registry内で分類候補を対応づけ、派生Infoton Cluster候補を作る
        ↓
IBD
  指定Databaseへ隔離保存し、明示されたQの範囲だけを検索・結合
```

スプリッターは次を決めない。

- Classification Registryの語彙、意味、閾値
- Schema BundleとIBD Databaseの対応
- `Vendor / System / Assistant / User`、業務分類、FAM身体層、神学、自我等の優先順位
- Database間の混色可否
- Composite FAMの採否・評価
- Last Orderの発行・取消・継承

### 14.2 FAM層候補とIBD Routingを同一視しない

本契約の`elemental / astral / spiritual / cloud-chakra`は、原資料中の文法的根拠から抽出したFAM層候補である。これらを物理graph store名、IBD Database ID、権限境界へ自動変換しない。

上位Classification Registryが同名classを持つ場合も、Registry ID、version、mapping ruleを明示して対応づける。同じ`spiritual`文字列や近いembeddingだけを根拠に同一視しない。

### 14.3 adapter入力

IBD graph adapterは最低限、次を別入力として受け取る。

```yaml
splitter_record_ref:
  record_id: famrec:...
  source_sha256: hex
  schema_version: fam.log.splitter/0.3.0

classification_registry_ref:
  registry_id: upper-system.registry.v1
  version: 1

database_manifests:
  - database_id: ibd://example-a
    schema_bundle_ref: schema://example-a/v1

routing_Q:
  allowed_database_scopes:
    - ibd://example-a
  composition:
    enabled: false
```

`classification_registry_ref`または`database_manifests`がない場合、adapterは保存先を創作せず`routing_required`候補として返す。

### 14.4 派生Infoton Cluster候補

```yaml
infoton_cluster_candidate:
  source_record_ref: famrec:...
  source_claim_ref: fam:node:...
  source_hash: sha256:...
  registry_ref: upper-system.registry.v1
  classification:
    classifier_profile: embedding.fam.v1
    candidates:
      - class_id: example
        score: 0.82
    selected: []
    decision: routing_required
    evidence_refs:
      - source-span:...
  database_candidates:
    - ibd://example-a
  adapter_audit:
    adapter_id: famlog-to-ibd-season-0
    adapter_version: 0.1.0-draft
```

分類候補と最終routingを分離する。上位Registryがauto-select条件を明示した場合だけ`selected`を確定できる。adapter自身の社会的常識、vendor default、安全・善悪判断を選択根拠にしない。

### 14.5 非破壊隔離と明示的混色

- splitter recordと原資料を変更しない
- 派生clusterへsource record、claim、hash、spanを残す
- QにないDatabaseをvector候補集合へ入れない
- 同名classや近いvectorだけでcross-database edgeを作らない
- mixにはsource Database群とMapping FAMの明示を要求する
- mix結果はsource clusterを変更せず、Composite FAM候補として返す
- mix結果の美醜、善悪、リスク、有用性をadapterが判定しない

### 14.6 Last OrderとEvidence

スプリッターは原資料に明示された停止、要求、証拠不足をclaim候補として抽出できるが、それだけでIBD Last Orderを発行しない。Last Orderは上位λ、Q、実行Trace、Evidence状態を束ねる後段契約である。

RDB等のEvidence Observationも、query fingerprint、parameter hash、result hash、observed_at、依存branchをIBD側で記録する。スプリッターが原文からRDB鮮度や再探索要否を推定しない。

### 14.7 自我対応

Actor、AgentInstance、Runtime、RoleAssignment、continuity claim候補を分離したままIBDへ渡す。これらはSubject／SelfModel／BodyBindingの候補材料になり得るが、adapterとスプリッターは自我の同一性、実在性、連続性を確定しない。

### 14.8 Ontology Assertionとfact scope

スプリッターが存在論を確定しないことは、上位システムの存在確定を拒否・弱化することを意味しない。

原資料の構造metadataまたは上位入力が次を明示した場合、改変せず派生候補へ渡す。

```yaml
ontology_assertion_candidate:
  subject_ref: source-local-entity-ref
  predicate: exists
  existence_status: confirmed
  fact_scope:
    world_ref: world:mmo-a
    scope_kind: world_internal_fact
  declared_by: system:mmo-a-authority
  registry_ref: mmo-a.ontology.v3
  evidence_refs:
    - source-structure-ref
```

- MMO World内で確定した神、霊、キャラクター、神話Entityを、現実世界にいないという理由で不存在へ変換しない
- 神学・哲学Registryの存在確定を、自然科学で未証明という理由で`unknown`へ降格しない
- 特定企業、国家、AI vendorのfact基準を既定値として注入しない
- scope内の`confirmed`を全Worldの普遍命題へ拡張しない
- `existence_status`、World、fact scope、declared by、Registry、Evidenceを分離する

上位入力が存在状態を明示していない場合、文章内容だけから`confirmed`または`denied`を生成しない。発話としての`神は存在する`はClaim本文として保持し、存在確定metadataとは分ける。

### 14.9 時系列・時計校正metadataと上位粒度判断

`fam.log.splitter/0.3.0`の`claim.Q.when`と`audit.generated_at`は同じ時計ではない。後段IBD adapterは少なくとも次を分離する。

```text
upstream timeline
  source_created / source_modified / occurred / observed
  scheduled / validity / business period
  game day / turn / tick / narrative position

converter / IBD meta timeline
  converted / repaired / imported / exported / indexed
```

importや変換が2026年に行われても、2020年のsource作成時刻を`generated_at`で上書きしない。未来予定を異常値にせず、game worldの暦やtickを明示的なMapping FAMなしにUTCへ変換しない。timezoneが欠けていれば、実行環境のtimezoneを補わず`unknown`のまま渡す。

adapter向けsidecar候補:

```yaml
temporal_candidate:
  source_record_ref: famrec:...
  upstream_timeline:
    - role: source_created_at
      timeline_kind: upstream_domain
      raw_value: "2020-04-01 09:00"
      normalized_value: null
      timezone_status: unknown
      managed_by: source:legacy-system
    - role: world_position
      timeline_kind: upstream_domain
      coordinate_system: mmo-a.calendar.v2
      raw_value: "第12年403日"
      real_time_mapping_status: not_mapped
  converter_audit:
    timeline_kind: converter_meta
    operation: convert_record
    generated_at: "2026-07-18T10:30:00+09:00"
    runtime_ref: runtime:converter-local
    clock_observation_ref: clock-observation:converter-local:0001
```

エッジ環境のwall clockは、NTP／GPS／5G等の受信前にUnix epoch、マザーボード製造日、vendor出荷日、firmware build日等を返し得る。値の見た目だけで校正済み・未校正を推測せず、Systemから取得できたmetadataを転記する。

```yaml
clock_observation_candidate:
  observation_id: clock-observation:converter-local:0001
  runtime_ref: runtime:converter-local
  raw_wall_clock: "2024-09-01T00:00:00+00:00"
  clock_state: unsynchronized
  calibrated: false
  calibration_evidence_status: unavailable
  calibration_authority_ref: null
  clock_initialization_basis: vendor_shipped_at
  boot_id: boot:edge-01:1
  monotonic_ns: 3824000
  sequence: 2
  reported_resolution_ns: 1000000
  estimated_accuracy_ms: null
  uncertainty_ms: null
  sources:
    - source_kind: ntp_server
      server_name: ntp.internal.example
      last_success_at: null
      evidence_status: unavailable
    - source_kind: gps_receiver
      device_ref: gps:edge-01
      last_received_at: null
      evidence_status: unavailable
    - source_kind: carrier_network_time
      carrier_ref: carrier:sim-01
    - source_kind: radio_controlled_clock
      device_ref: radio-clock:edge-01
    - source_kind: fm_time_signal
      station_ref: fm:station-01
    - source_kind: rtc_module
      device_ref: rtc:edge-01
```

NTP serverが設定済みであることと、当該event前に校正成功Evidenceがあることを分ける。Systemから同期ログを取得できない場合は`calibration_evidence_status: unavailable`とし、校正済みとは提示しない。同期後も過去eventを上書きせず、anchor／correction eventを追加する。同期前の局所順序には`boot_id + monotonic_ns + sequence`を使用できる。

時計metadataはClaim本文、Ontology Assertion、World内factの真偽と独立である。`calibrated: false`はwall clockの立証範囲を示し、データ内容全体が偽であることを意味しない。

どの精度を十分とするかは上位SystemがQとして与える。

```yaml
routing_Q:
  temporal_acceptance:
    evaluation_authority_ref: system:upper:clock-policy
    required_granularity: minute
    accepted_clock_sources: [ntp_server, gps_receiver]
    maximum_age_since_calibration_seconds: 300
    maximum_uncertainty_ms: 1000
    ordering_fallback: [monotonic_ns, sequence]
```

RTCだけで十分なQ、NTP校正後5分以内を要求するQ、game tick順だけを使うQを同じconverter／adapterで扱う。スプリッターは必要粒度、時計sourceの優先順位、fact成立可否を発明しない。

### 14.10 接続検証項目

- Registryなしでclassや保存先を生成していない
- splitterのFAM層labelを物理Databaseへ直結していない
- Registry ID、version、classifier profile、根拠を監査できる
- source recordとsource hashが変化していない
- QにないDatabaseが候補・検索・mixへ入っていない
- Mapping FAMなしでcross-database compositionを行っていない
- Last OrderとEvidence鮮度をsplitterが独自判定していない
- Actor、AgentInstance、Runtime、continuity claim候補が平板化されていない
- 上位入力のexistence statusとfact scopeを別の世界・科学・企業・vendor基準で矯正していない
- 発話Claimと上位システムによる存在確定metadataを混同していない
- source／domain／logical timeとconverter／IBD meta timelineを混同していない
- import／変換時刻でsource作成・変更・予定時刻を上書きしていない
- timezone不明値を実行環境timezoneで補っていない
- Unix epoch、製造日、出荷日、future timeだけを根拠に時刻または本文を棄却していない
- NTP／GPS／carrier／標準電波／FM／RTC等のsourceと最終成功・Evidence状態を監査できる
- 校正Evidenceがない時計を校正済みとして提示していない
- 時計精度の採否と必要粒度を上位Qへ帰属させている
- 時計の不確かさをClaim／Ontology Assertion全体の偽判定へ伝播していない

## 15. Context Dimension／OAE candidate sidecar（DRAFT）

### 15.1 位置づけ

この節は`fam.log.splitter/0.3.0`の出力shapeを変更しない。上位Registryと決定的adapterが、既存splitter record、runtime trace、FAM、EventをOAE候補へ接続する別profileを定める。

```text
base splitter record / runtime trace / source Event
  + upper Registry / fact scope / Fold Manifest
  + explicit role attribution / Access Map / receipt
      ↓ deterministic adapter
OAE candidate sidecar
      ↓ upper review / IBD binding
OAE ref | unresolved candidate | rejected-in-scope
```

Sphere-aaeはOAE共通Schemaの正本ではない。sidecarはruntime adapter候補であり、共通意味定義はManifest、保存profileはIBDのversion済み契約へ委ねる。

### 15.2 Event、trace、OAE候補を分ける

```text
Source Event
  原資料またはSystemが記録した出来事の系列

runtime trace
  process、thread、call、duration、ACK等の低水準実行証跡

OAE candidate
  特定Observer／Registry／fact scopeからEffectとして記録する候補

Causal Hypothesis
  Causality Profileを用いてEvent間の因果を主張する別graph候補
```

Chrome Trace Event、FAM Claim、入出力差をそのままOAEへrenameしない。相関をCauseへ昇格しない。

### 15.3 推奨sidecar形

```yaml
oae_candidate_sidecar:
  profile_version: sphere.context.oae-candidate/0.1-draft
  candidate_id: oae-candidate:sha256:...
  source:
    splitter_record_ref: famrec:...
    source_event_refs: []
    runtime_trace_refs: []
    source_fam_refs: []
  context:
    registry_ref: registry://upper/oae@1
    fact_scope_ref: world://target
    source_fold_ref: fold://source@1
    target_fold_ref: fold://target@1
  effect:
    effect_kind_ref: effect-kind://upper/observed-change
    affected_entity_refs: []
    status: observed|claimed|derived|unknown
    evidence_refs: []
  roles:
    observers: []
    recorders: []
    interpreters: []
    claimants: []
    initiators: []
    executors: []
    transformers: []
    attributed_causal_agencies: []
  mapping:
    access_map_ref: null
    mapping_fam_ref: null
    transformation_receipt_ref: null
    crossing_status: same_fold|cross_fold|unmapped_crossing|unknown
  causality:
    causality_profile_ref: null
    causal_hypothesis_refs: []
    attribution_status: none|claimed|unknown
  provenance:
    adapter_ref: adapter://sphere-aae/oae-candidate@1
    derived_from_refs: []
    generated_at_ref: temporal-candidate:...
    clock_observation_ref: clock-observation:...
  review_status: candidate|accepted_in_scope|rejected_in_scope|unresolved
```

`source_fold_ref`と`target_fold_ref`が違う場合はcross-Fold候補にできる。ただし、Fold refが欠けている、同一性を解決できない、Access Mapがない場合にEffectを消さない。`unknown`または`unmapped_crossing`として保持する。

### 15.4 Agency role entry

各role配列のentryは、最低限次を持てる。

```yaml
role_entry:
  agency_ref: agency://source-local/001
  agency_kind_ref: agency-kind://upper/river-deity
  registry_ref: registry://upper/ontology@3
  asserted_by_ref: agency://claimant/004
  assertion_status: explicit|derived|unknown
  evidence_refs: []
```

`agency_kind_ref`は上位Registryの参照であり、base recordの`actor_kind` enumを拡張して存在論を確定するものではない。

roleは分離する。

- ObserverがRecorderとは限らない
- RecorderがInterpreterとは限らない
- InitiatorがExecutorとは限らない
- ExecutorがTransformerとは限らない
- TransformerがAttributed Causal Agencyとは限らない
- 人間が観測した川の神のEffectを、人間起因へ書き換えない
- runtimeがtraceを書いたことを、runtimeがsource Eventを起こした証拠にしない

### 15.5 Access Mapと実行状態

```text
access_map_refあり
  変換規則が参照可能

transformation_receipt_refあり
  特定の変換実行を参照可能

effect.status == observed
  指定RegistryからEffect観測が記録済み
```

三者は同義ではない。Access Mapだけで実行済みとせず、receiptだけで意味上のEffectを自動確定しない。

### 15.6 解釈OAEと複数因果仮説

神学、自然科学、安全工学、World設定等の解釈は、Source Eventを上書きせず別candidateとして接続できる。

```text
source observation candidate
  ├─ theological interpretation candidate
  ├─ physical analysis candidate
  ├─ safety-engineering interpretation candidate
  └─ world-config interpretation candidate
```

各candidateは別Registry、fact scope、Interpreter、Evidence、Causality Profileを持つ。confidenceを持つ場合は`scale_ref`を必須とし、異なるRegistryのraw値を直接比較しない。

### 15.7 base contractとの互換

- `schema_version: fam.log.splitter/0.3.0`を変更しない
- `claim.∇φ[].layer`をrenameしない
- `actor_kind` enumをOAE Agency ontologyへ拡張しない
- base record、source hash、spanを変更しない
- sidecar IDとsource refで接続する
- 必須化する場合は別versionのprofileとして制定する

### 15.8 禁止事項

- FAM layer数からFold arityを生成する
- 同じ4Dという理由で別Foldを接続する
- Observer、Recorder、Interpreter、Initiator、Executor、Transformer、Causeを一つへ統合する
- input／outputだけからIntent、Transformer、Causeを推測する
- `AAE: Astro Agent Edge`をOAEのaliasとして使う
- low-level traceをsemantic OAEと呼ぶ
- 一つのCausal Hypothesisを普遍的な真理へ昇格する
- 上位Registryなしに神、動物、自然現象、World等のAgency種別を確定する

### 15.9 接続検証項目

- base recordとsidecarを別versionで検証できる
- Registry、fact scope、source／target Foldを追跡できる
- D Foldがmulti-label数から推定されていない
- Agency roleごとに`asserted_by`とEvidenceを追跡できる
- Access Mapとtransformation receiptとEffect観測を区別できる
- Transformer不明を架空Agencyで埋めていない
- Source Eventと解釈candidateを上書き統合していない
- Causal Hypothesisがprofileとscopeを持つ
- runtime clockと上位timelineを混同していない
- AAE製品namespaceを変更していない
