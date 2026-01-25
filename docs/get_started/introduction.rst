.. _introduction-to-mlc-llm:

MLC LLM の紹介（Introduction to MLC LLM）
=======================================

.. contents:: 目次（Table of Contents）
    :local:
    :depth: 2

MLC LLM は大規模言語モデル（Large Language Models: LLMs）向けの機械学習コンパイラ（Machine Learning Compiler）
および高性能デプロイメントエンジン（High-performance Deployment Engine）です。本プロジェクトの使命（mission）は、
誰もがあらゆるプラットフォーム上でAIモデルをネイティブに開発・最適化・デプロイできるようにすることです。 

このページは、MLC LLM を試す方法と、MLC LLM で独自モデルをデプロイするまでの手順を紹介するクイックチュートリアルです。

インストール（Installation）
----------------------------

:ref:`MLC LLM <install-mlc-packages>` は pip で入手できます。
分離された conda 仮想環境（conda virtual environment）にインストールすることを常に推奨します。

インストール確認のため、仮想環境を有効化して次を実行します。

.. code:: bash

  python -c "import mlc_llm; print(mlc_llm.__path__)"

MLC LLM の Python パッケージのインストールパスが表示されるはずです。


チャットCLI（Chat CLI）
----------------------

最初の例として、4-bit 量子化（quantized）された 8B Llama-3 モデルで MLC LLM のチャット CLI を試します。
次のワンライナーコマンドで MLC chat を実行できます。

.. code:: bash

    mlc_llm chat HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC

初回実行時は 1〜2 分ほどかかる場合があります。
待機後、このコマンドはチャットインターフェースを起動し、プロンプトを入力してモデルと対話できます。

.. code::

  You can use the following special commands:
  /help               print the special commands
  /exit               quit the cli
  /stats              print out the latest stats (token/sec)
  /reset              restart a fresh chat
  /set [overrides]    override settings in the generation config. For example,
                        `/set temperature=0.5;max_gen_len=100;stop=end,stop`
                        Note: Separate stop words in the `stop` option with commas (,).
  Multi-line input: Use escape+enter to start a new line.

  user: What's the meaning of life
  assistant:
  What a profound and intriguing question! While there's no one definitive answer, I'd be happy to help you explore some perspectives on the meaning of life.

  The concept of the meaning of life has been debated and...


以下の図は、このチャット CLI コマンドの内部処理を示しています。
初回実行時には、主に 3 つのフェーズがあります。

- **フェーズ 1. 事前量子化（pre-quantized）重みのダウンロード。** `Hugging Face <https://huggingface.co/mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC>`_ から事前量子化済み Llama-3 モデルを自動的にダウンロードし、ローカルのキャッシュディレクトリに保存します。
- **フェーズ 2. モデルのコンパイル。** `Apache TVM <https://llm.mlc.ai/docs/install/tvm.html>`_ コンパイラの機械学習コンパイル技術を用いて Llama-3 モデルを自動的に最適化し、GPU 推論を高速化します。同時に、ローカル GPU 上で言語モデルを実行するためのバイナリモデルライブラリを生成します。
- **フェーズ 3. チャットランタイム。** フェーズ 2 で構築したモデルライブラリとフェーズ 1 でダウンロードしたモデル重みを使用して、プラットフォームネイティブのチャットランタイムを起動し、Llama-3 モデルを実行します。

事前量子化済みモデル重みとコンパイル済みモデルライブラリはローカルにキャッシュされます。
そのため、フェーズ 1 と 2 は複数回の実行に対して **一度だけ** 実行されます。

.. figure:: /_static/img/project-workflow.svg
  :width: 700
  :align: center
  :alt: Project Workflow

  Workflow in MLC LLM

.. note::

  複数 GPU で LLM を実行するためにテンソル並列（tensor parallelism）を有効化したい場合は、
  ``--overrides "tensor_parallel_shards=$NGPU"`` を指定してください。
  例：

  .. code:: shell

    mlc_llm chat HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC --overrides "tensor_parallel_shards=2"

.. _introduction-to-mlc-llm-python-api:

Python API
----------

2 つ目の例として、MLC LLM のチャット補完（chat completion）Python API を使って Llama-3 モデルを実行します。
以下のコードを Python ファイルに保存して実行できます。

.. code:: python

  from mlc_llm import MLCEngine

  # Create engine
  model = "HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC"
  engine = MLCEngine(model)

  # Run chat completion in OpenAI API.
  for response in engine.chat.completions.create(
      messages=[{"role": "user", "content": "What is the meaning of life?"}],
      model=model,
      stream=True,
  ):
      for choice in response.choices:
          print(choice.delta.content, end="", flush=True)
  print("\n")

  engine.terminate()

.. figure:: https://raw.githubusercontent.com/mlc-ai/web-data/main/images/mlc-llm/tutorials/python-engine-api.jpg
  :width: 500
  :align: center

  MLC LLM Python API

このコード例では、4-bit 量子化された Llama-3 モデルで :class:`mlc_llm.MLCEngine` インスタンスを作成します。
**Python API の :class:`mlc_llm.MLCEngine` は OpenAI API に合わせて設計**されているため、
`OpenAI の Python パッケージ <https://github.com/openai/openai-python?tab=readme-ov-file#usage>`_ と同様の方法で
同期・非同期の生成に利用できます。

このコード例では同期的なチャット補完インターフェースを使い、ストリーム応答をすべて反復処理しています。
ストリーミングなしで実行したい場合は、次のようにします。

.. code:: python

  response = engine.chat.completions.create(
      messages=[{"role": "user", "content": "What is the meaning of life?"}],
      model=model,
      stream=False,
  )
  print(response)

`OpenAI chat completion API <https://platform.openai.com/docs/api-reference/chat/create>`_ がサポートする各種引数も利用できます。
並行した非同期生成を行いたい場合は、代わりに :class:`mlc_llm.AsyncMLCEngine` を使用してください。

.. note::

  複数 GPU で LLM を実行するためにテンソル並列（tensor parallelism）を有効化したい場合は、
  MLCEngine コンストラクタの ``model_config_overrides`` 引数を指定してください。
  例：

  .. code:: python

    from mlc_llm import MLCEngine
    from mlc_llm.serve.config import EngineConfig

    model = "HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC"
    engine = MLCEngine(
        model,
        engine_config=EngineConfig(tensor_parallel_shards=2),
    )


REST サーバー（REST Server）
----------------------------

3 つ目の例として、4-bit 量子化された Llama-3 モデルを OpenAI チャット補完リクエスト向けに提供する REST サーバーを起動します。
サーバーはコマンドラインで次のように起動できます。

.. code:: bash

  mlc_llm serve HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC

サーバーは既定で ``http://127.0.0.1:8000`` にバインドされます。``--host`` と ``--port`` を使って別のホストやポートを設定できます。
サーバーの準備ができたら（``INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`` と表示されたら）、
新しいシェルを開き、以下のコマンドで cURL リクエストを送信します。

.. code:: bash

  curl -X POST \
    -H "Content-Type: application/json" \
    -d '{
          "model": "HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC",
          "messages": [
              {"role": "user", "content": "Hello! Our project is MLC LLM. What is the name of our project?"}
          ]
    }' \
    http://127.0.0.1:8000/v1/chat/completions

サーバーがリクエストを処理し、応答を返します。
:ref:`introduction-to-mlc-llm-python-api` と同様に、ストリーム応答を要求するには ``"stream": true`` を指定できます。

.. note::

  複数 GPU で LLM を実行するためにテンソル並列（tensor parallelism）を有効化したい場合は、
  ``--overrides "tensor_parallel_shards=$NGPU"`` を指定してください。
  例：

  .. code:: shell

    mlc_llm serve HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC --overrides "tensor_parallel_shards=2"

.. _introduction-deploy-your-own-model:

独自モデルのデプロイ（Deploy Your Own Model）
----------------------------------------------

これまでは Hugging Face の変換済みモデル重みを使用してきました。
このセクションでは、*MLC LLM で独自モデルを実行する* ための中核ワークフローを紹介します。

例として `Phi-2 <https://huggingface.co/microsoft/phi-2>`_ モデルを使用します。
Phi-2 モデルがダウンロードされ ``models/phi-2`` に配置されていると仮定すると、
独自モデルを準備するための大きな手順は 2 つです。

- **ステップ 1. MLC 設定（config）を生成。** 最初のステップは MLC LLM の設定ファイルを生成することです。

  .. code:: bash

    export LOCAL_MODEL_PATH=models/phi-2   # The path where the model resides locally.
    export MLC_MODEL_PATH=dist/phi-2-MLC/  # The path where to place the model processed by MLC.
    export QUANTIZATION=q0f16              # The choice of quantization.
    export CONV_TEMPLATE=phi-2             # The choice of conversation template.
    mlc_llm gen_config $LOCAL_MODEL_PATH \
        --quantization $QUANTIZATION \
        --conv-template $CONV_TEMPLATE \
        -o $MLC_MODEL_PATH

  設定生成コマンドは、ローカルモデルパス、MLC 出力先パス、
  MLC における会話テンプレート名（conversation template）、
  MLC における量子化名（quantization）を受け取ります。
  ここで量子化 ``q0f16`` は量子化なしの float16 を意味し、
  会話テンプレート ``phi-2`` は MLC における Phi-2 モデルのテンプレートです。

  複数 GPU でテンソル並列を有効化したい場合は、
  設定生成コマンドに ``--tensor-parallel-shards $NGPU`` を追加してください。

  - `MLC でサポートされる量子化の完全な一覧 <https://github.com/mlc-ai/mlc-llm/blob/main/python/mlc_llm/quantization/quantization.py#L29>`_。MLC LLM で異なる量子化方式を試せます。代表的な方式は、4-bit グループ量子化の ``q4f16_1``、4-bit FasterTransformer 形式量子化の ``q4f16_ft`` などです。
  - `MLC における会話テンプレートの完全な一覧 <https://github.com/mlc-ai/mlc-llm/blob/main/python/mlc_llm/interface/gen_config.py#L276>`_。

- **ステップ 2. モデル重みの変換。** このステップでモデル重みを MLC 形式へ変換します。

  .. code:: bash

    mlc_llm convert_weight $LOCAL_MODEL_PATH \
      --quantization $QUANTIZATION \
      -o $MLC_MODEL_PATH

  このステップでは生のモデル重みを消費し、MLC 形式へ変換します。
  変換済み重みは ``$MLC_MODEL_PATH`` に保存され、これはステップ 1 の設定ファイルが生成されたディレクトリと同一です。

これで、チャット CLI で独自モデルを実行できます。

.. code:: bash

  mlc_llm chat $MLC_MODEL_PATH

初回実行時は、モデルの JIT コンパイルが自動的にトリガーされ、
GPU 向けに最適化されたバイナリモデルライブラリが生成されます。
チャットインターフェースはモデル JIT コンパイル完了後に表示されます。
このモデルは Python API、MLC serve など他の利用シナリオでも使用できます。

（任意）モデルライブラリのコンパイル（Compile Model Library）
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

前のセクションでは、:class:`mlc_llm.MLCEngine` の起動時にモデルライブラリをコンパイルします。
これが「JIT（Just-in-Time）モデルコンパイル」と呼ばれるものです。
場合によっては、明示的にモデルライブラリをコンパイルすることが有益です。
コンパイルを経ずにデプロイ用ライブラリを配布することで、依存関係を減らした LLM デプロイが可能になります。
また、Web やモバイル向けのクロスコンパイルなど高度なオプションも利用できます。

以下は MLC LLM でモデルライブラリをコンパイルするコマンド例です。

.. code:: bash

  export MODEL_LIB=$MLC_MODEL_PATH/lib.so  # ".dylib" for Intel Macs.
                                            # ".dll" for Windows.
                                            # ".wasm" for web.
                                            # ".tar" for iPhone/Android.
  mlc_llm compile $MLC_MODEL_PATH -o $MODEL_LIB

実行時は、このモデルライブラリのパスを指定する必要があります。例：

.. code:: bash

  # For chat CLI
  mlc_llm chat $MLC_MODEL_PATH --model-lib $MODEL_LIB
  # For REST server
  mlc_llm serve $MLC_MODEL_PATH --model-lib $MODEL_LIB

.. code:: python

  from mlc_llm import MLCEngine

  # For Python API
  model = "models/phi-2"
  model_lib = "models/phi-2/lib.so"
  engine = MLCEngine(model, model_lib=model_lib)

:ref:`compile-model-libraries` でモデルコンパイルコマンドの詳細を紹介しています。
WebGPU、iOS、Android などの各ハードウェアバックエンドに対するコンパイル手順や例を確認できます。

ユニバーサルデプロイ（Universal Deployment）
---------------------------------------------

MLC LLM は大規模言語モデル向けの高性能なユニバーサルデプロイソリューションであり、
コンパイラによる高速化で、あらゆる大規模言語モデルをネイティブ API でデプロイできるようにします。
これまでにローカル GPU 環境での例をいくつか見てきました。
本プロジェクトは複数種類の GPU バックエンドをサポートしています。

コンパイル時および実行時に `--device` オプションを用いて特定の GPU バックエンドを選択できます。
たとえば NVIDIA または AMD GPU がある場合、以下のオプションで Vulkan バックエンドを使ったチャットを実行できます。
Vulkan ベースの LLM アプリケーションは、Steam Deck などの非典型的な環境でも動作します。

.. code:: bash

    mlc_llm chat HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC --device vulkan

同一のコア LLM ランタイムエンジンがすべてのバックエンドで動作するため、
対象ハードウェアのメモリ・計算予算に収まる限り、同じモデルをバックエンド間でデプロイできます。
また、機械学習コンパイルを活用してバックエンド特化の最適化を構築し、
可能な限り対象バックエンドで最高の性能を引き出しつつ、
各バックエンド間で重要な知見と最適化を再利用します。

WebGPU ベースのブラウザデプロイ、モバイルなど、
さまざまなデプロイシナリオについては、以下の「次にやること」を参照してください。

まとめと次にやること（Summary and What to Do Next）
-----------------------------------------------------

このページの要点を簡潔にまとめると、

- MLC LLM の 3 つの例（チャット CLI、Python API、REST サーバー）を確認しました。
- MLC LLM で独自モデルを実行するための重み変換と、（任意で）モデルのコンパイル方法を紹介しました。
- MLC LLM のユニバーサルデプロイ能力についても説明しました。

次に、以下のページでクイックスタート例と、特定プラットフォーム向けの詳細情報を確認してください。

- Python API、チャット CLI、REST サーバー、Web ブラウザ、iOS、Android の :ref:`クイックスタート例 <quick-start>`。
- ユースケースに応じて、API ドキュメントとチュートリアルの各ページを参照してください。

  - :ref:`webllm-runtime`
  - :ref:`deploy-rest-api`
  - :ref:`deploy-cli`
  - :ref:`deploy-python-engine`
  - :ref:`deploy-ios`
  - :ref:`deploy-android`
  - :ref:`deploy-ide-integration`

- 独自モデルを実行したい場合は、:ref:`MLC 形式へのモデル重み変換 <convert-weights-via-MLC>` を参照してください。
- Web/iOS/Android へのデプロイやモデル最適化の制御を行いたい場合は、:ref:`モデルライブラリのコンパイル <compile-model-libraries>` を参照してください。
- 問題報告や質問は `GitHub リポジトリ <https://github.com/mlc-ai/mlc-llm/issues>`_ に新しい Issue を作成してください。
