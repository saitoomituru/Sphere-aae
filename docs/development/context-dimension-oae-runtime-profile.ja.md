# Sphere-aae Context Dimension／OAE runtimeプロファイル

状態: `[DRAFT]` `[RUNTIME-PROFILE]`  
更新日: 2026-07-18  
対象: Sphere-aae runtime、system-call splitter、FAMLog adapter、IBD接続

## 1. 共通正本との境界

Context Dimension、D Fold、Registry／Context Register、Access Map、Transformer、OAEの共通定義はZeroRoomLab-manifestの[Sphere Context Dimension OSアーキテクチャ](https://github.com/saitoomituru/ZeroRoomLab-manifest/blob/main/docs/theory/sphere-context-dimension-os.ja.md)を参照する。

Sphere-aaeは共通存在論やOAE保存正本を制定しない。runtimeで発生したsystem call、FAM routing、変換、LAST_ORDERを観測し、上位RegistryとIBDへ渡せるproducer／consumer adapter候補である。

## 2. AAEとOAEのnamespace

```text
AAE  Astro Agent Edge
     本リポジトリ、package、CLI、mobile binding、生成物の既存製品namespace

OAE  Observer Agential Effect
     Sphere Architect全般で観測されたEffectを管理する共通概念namespace
```

AAEをOAEへrenameしない。`sphere_aae` package、`AAE`表記、既存artifact suffixは互換境界である。OAE参照を扱う場合は`oae://`等の別namespaceを使用する。

## 3. 二種類のSplitter

### 3.1 system-call splitter

Sphere-aae runtime内で、model intentをASTRO、IBD、tool、sensor、reboot、language generation等の技術routeへ分岐する。ACK、payload validation、state commit、LAST_ORDERを扱う。

### 3.2 FAM Splitter

FAM／FAMLogを上位RegistryのContext Dimension候補へ分類し、IBD Databaseへのroute候補と根拠を返す。IBDSDKの差替可能SPIとして定義され、Sphere-aaeのsystem-call splitterと同一moduleではない。

```text
system-call splitter = 実行callの技術routing
FAM Splitter         = 上位定規に従うContext分類候補
```

同じ実装が両capabilityをbundleする可能性はあるが、receipt、責務、failure、versionを分ける。

## 4. `L`、`D`、FAM label

```text
technical Layer L
  runtime、router、adapter、store等の依存・実行順

Context Dimension D
  上位RegistryがFoldへ束ねる等価な意味軸

legacy FAM layer label
  elemental / astral / spiritual / cloud-chakraの文法分類候補
```

FAMのmulti-label候補数をD Foldの軸数としない。D FoldはFold ID、revision、Dimension refsを持つManifestで上位Systemが宣言する。

FAMの「縦方向・再帰方向」は探索topologyであり、技術Layer `L`の上下を意味しない。`λ=出力層`もFAM記号の歴史的Presentationであり、technical layer keyではない。

## 5. 初期起動比較フレーム

```text
System
  > Spiritual Body
  > Astral Body
  > Elemental Body
```

この順序は、Sphere-aae起動時に競合命令を比較する明示的な**boot priority／Access Map profile**である。すべてのSDK、World、FAM、Context Dimensionへ普遍的な上下関係を与えない。

一般Agentの`system > developer > user`へ接続する場合は、無条件の同一視ではなくversion付きMapping Profileを使う。変換元、変換先、優先規則、loss、unknown、適用範囲をreceiptへ残す。

## 6. Access Map、Transformer、OAE

```text
Access Map
  どのruntime contextから何へroute／変換できるかの静的規則

Transformer
  その規則を使い能動変換するAgency／function

OAE
  変換、解釈、分類、作用が観測されたContext記録
```

Access Mapがロード済みでもEffectが起きたとは限らない。system callが要求されたこと、ACKされたこと、payloadが検証されたこと、state commitされたことを別状態で保持する。

inputとoutputだけからTransformer、Intent、Causeを推定生成しない。Fold越境が観測できてもTransformer不明なら`unknown`を保持する。

## 7. Agency role

OAE候補では次を分離する。

- Observer
- Recorder
- Interpreter
- Claimant
- Initiator
- Executor
- Transformer
- Attributed Causal Agency
- Environment
- Affected Entity

Sphere-aae runtimeが記録したという理由で、runtimeをEffectの原因へ昇格しない。Userがsystem callを依頼したこと、modelがrouteしたこと、driverが実行したこと、deviceが作用したこと、observerが結果を記録したことを平板な一つの`actor`へ畳まない。

## 8. runtime traceとOAE

既存`event_trace_recorder.py`が扱うChrome Trace Eventは、process／thread／duration等の低水準実行証跡であり、OAEではない。

```text
low-level runtime trace
  + upper Registry
  + role attribution
  + fact scope
  + source Event / FAM
  + Access Map / transformation receipt
      ↓ deterministic adapter
OAE candidate sidecar
```

一つのruntime traceから複数OAE候補が派生する場合も、semantic Effectへ昇格されない場合もある。元traceを上書きしない。

## 9. FAMLog sidecar

既存`fam.log.splitter/0.3.0`の安定shapeとlegacy `layer` fieldを破壊しない。Context Dimension、Agency role、Access Map、Fold越境、因果仮説は別sidecar profileとして接続する。

sidecarは次を創作しない。

- FAM labelからD Foldを推定する
- `actor_kind`から存在論を確定する
- ObserverをCauseへ昇格する
- 入出力差だけからTransformerを特定する
- 相関だけからCausal Hypothesisを採用する

詳細候補は[fam-log-schema §15](../../skills/famlog-converter/references/fam-log-schema.md#15-context-dimensionoae-candidate-sidecar-draft)を参照する。

## 10. Sphere-aaeが担当しないもの

- OAE共通Schemaの正本化
- IBD Store／DatabaseのClassification Registry制定
- FAM Splitter汎用SPIの正本化
- 神学、物理、World、人格のfact定規制定
- AstroSDK／Atlantis SDKのD Fold Manifest制定
- low-level traceだけからの責任・因果判定

## 11. 合格条件

- AAE製品namespaceとOAE概念namespaceが分離される
- system-call splitterとFAM Splitterのreceiptが分離される
- boot priority profileをD Foldの普遍的上下へしない
- FAM label数からD数を推定しない
- Access MapをEffect発生済みとしない
- Observer、Recorder、Initiator、Executor、Transformer、Causeを平板化しない
- Chrome Trace EventをOAEと呼ばない
- 既存FAMLog 0.3.0を破壊せずsidecarで拡張する

