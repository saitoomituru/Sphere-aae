# MLC-LLM ドキュメント（Documentation）

このドキュメントは [Sphinx](https://www.sphinx-doc.org/en/master/) により構築されています。

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

## ドキュメントの閲覧（View the Documentation）

次のコマンドでシンプルなHTTPサーバーを起動します。

```bash
cd _build/html
python3 -m http.server
```

その後、ブラウザで `http://localhost:8000` を開いてドキュメントを閲覧できます（ポートは上記の Python コマンドに ` -p PORT_NUMBER` を付けて変更可能です）。
