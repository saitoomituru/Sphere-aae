# Sphere-aae Python／Venv運用profile.proton

状態: `[DRAFT]` `[AAE ADOPTION PROFILE]` `[NO RUNTIME CHANGE]`

upstream: `proton://zeroroomlab/python-venv-operations@1`

upstream revision: `ZeroRoomLab-manifest@799d36e`

正本: [Python／Venv運用の虎の巻.proton](https://github.com/saitoomituru/ZeroRoomLab-manifest/blob/main/docs/operations/python-venv-operations.proton.md)

## 1. 適用範囲

このProtonは、ZeroRoomLab横断のPython／Venv contractをSphere-aaeへどう採用するか宣言する。
`sphere_aae` package、MLC／TVM build、accelerator、Apple／CUDA runtimeの既存正本を置換しない。

```yaml
proton_adoption:
  id: proton-adoption://sphere-aae/python-venv-operations@1
  upstream: proton://zeroroomlab/python-venv-operations@1
  package_contract: pyproject.toml
  package_requires_python: ">=3.9"
  new_operations_tools_default: ">=3.11"
  bootstrap_implementation: NOT_IMPLEMENTED
  disposable_browser_observer: PROVIDED_BY_ATLANTIS_PROFILE
```

## 2. AAE固有のprofile分離

Sphere-aaeはPython packageだけでなく、CMake、C++、TVM、Metal／Core ML、CUDA、model weight、device runtimeを
含む。`pip install`が成功しただけでruntime全体を構築済みにしない。

| profile | 主な対象 | 別profileへ混ぜないもの |
|---|---|---|
| `control` | 軽量validator、文書、Schema、運用tool | torch、TVM build、model weight |
| `cpu-runtime` | CPU build、reference test | Metal／CUDA artifact |
| `apple-runtime` | macOS、Metal、Core ML実測 | CUDA／Linux専用wheel |
| `cuda-runtime` | Linux、CUDA、GPU test | Apple framework |
| `browser-observer` | Git／Webの明示URL観測 | model runtime、認証cookie、weight |

実directory名、Python minor、依存lockは各build profile確定時に定める。同じ`.venv`へprofileを上書き導入して
結果を比較せず、OS／architecture／accelerator／Python／dependency manifestをreceiptへ残す。

## 3. 既存package契約を守る

root `pyproject.toml`は`requires-python = ">=3.9"`を宣言している。この採用profileは、AAE packageの
対応下限をPython 3.11へ黙って引き上げない。

一方、今後追加するZeroRoomLab固有の運用CLI、clean-room、receipt validatorはPython 3.11以上を既定にできる。
package runtimeと運用toolのPython範囲が異なる場合は、別entrypoint、別Venv、別CI jobとして表示する。

## 4. 禁止するVenv loop

- 対象`.venv`自身のPythonから同じ`.venv`へ`venv.EnvBuilder.create()`を再実行しない。
- AAE rootの依存を3rdparty subtreeのVenvへ導入しない。
- 3rdpartyのrequirementsをroot profileへ機械結合しない。
- Appleで作ったVenvをLinux／CUDAへcopyしない。
- accelerator package不成立時にCPU成功へsilent fallbackしない。
- 壊れたVenvを自動削除しない。

`READY`なVenvは再利用receiptを返す。`STALE`、`INCOMPATIBLE`、`BROKEN`は原因とprofileを返し、人間が
対象pathを明示して再生成する。

## 5. Browser観測はAtlantis別枠

SaaS検索やconnector要約は`INDEXED_SNAPSHOT`、明示URLをheadless browserで開いた結果は
`BROWSER_OBSERVED`として分ける。後者もCDN／server cacheを通り得るためorigin freshとは断定しない。

Selenium／ChromiumはAAE model runtimeへbundleせず、SphereOS Atlantisの使い捨てBrowser観測profileを使う。
AAE側に必要になった場合も、model weight、provider認証、host keychain、Docker socketを渡さない別containerと
別Venvで実行する。

ブラクラ等の復旧単位はVenvだけでなく、browser process、tmp user-data-dir、download、一時container／volumeを
含む。VenvはPython package隔離であり、browser／kernel sandboxの代用品ではない。

## 6. AAE向けreceipt追加

```yaml
aae_python_receipt:
  source_revision: null
  profile: control | cpu-runtime | apple-runtime | cuda-runtime | browser-observer
  python_version: null
  os: null
  architecture: null
  accelerator: none | cpu | metal | coreml | cuda | unknown
  dependency_manifest: null
  tvm_revision: null
  model_weight_loaded: false
  runtime_tested: false
  network_access: not-requested | performed | unknown
  fallback_performed: false
  unknown: []
```

`import sphere_aae`、wheel生成、model load、token生成、system-call splitter、FAM routing、device実行を別testとして
記録する。一段の成功を全経路成功へ拡張しない。

## 7. 実装予定

1. root／upstream buildと衝突しないprofile manifestを決める。
2. control profile用の依存最小集合を抽出する。
3. CPU、Apple、CUDAのclean-room receiptを別jobで生成する。
4. Venv bootstrapはAtlantis reference実装の不変条件を採用し、AAE固有buildを別hookへ置く。
5. browser observationはAtlantis profileとの接続testだけを持ち、AAE core依存にしない。

この文書追加時点ではAAE用bootstrap、profile lock、clean-room CIは`NOT IMPLEMENTED`である。
