# Sphere-aae ドキュメント（Documentation）

このドキュメントは [Sphinx](https://www.sphinx-doc.org/en/master/) により構築されています。

## 役割分担（手書き vs 自動生成）

- **手書きドキュメント**：思想・概念・チュートリアル・設計方針の説明を担当します。
- **自動生成ドキュメント**：API 仕様（Python モジュールの参照情報）を担当します。

自動生成の出力先は `docs/api/_generated/` で、`sphinx-apidoc` によって更新されます。
このディレクトリの rst はコミット対象（テンプレート）とし、HTML は生成物としてコミットしません。

## 依存関係（Dependencies）

まず、このディレクトリで以下のコマンドを実行して依存関係をインストールします。

```bash
pip3 install -r requirements.txt
```

## ドキュメントのビルド（Build the Documentation）

次に、以下のコマンドでドキュメントをビルドできます。

```bash
make html
```

## API 仕様の自動生成（sphinx-apidoc）

API 仕様の rst を生成してからビルドする場合は、以下を実行します。

```bash
../scripts/docs_generate.sh
```

## ドキュメントの閲覧（View the Documentation）

次のコマンドでシンプルなHTTPサーバーを起動します。

```bash
cd _build/html
python3 -m http.server
```

その後、ブラウザで `http://localhost:8000` を開いてドキュメントを閲覧できます（ポートは上記の Python コマンドに ` -p PORT_NUMBER` を付けて変更可能です）。
