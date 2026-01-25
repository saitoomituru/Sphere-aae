.. _quick-start:

クイックスタート（Quick Start）
===============================

例（Examples）
--------------

まずは、int4 量子化（int4-quantized）された Llama3 8B に対する MLC LLM のサポートを試してください。
実行には少なくとも 6GB の空き VRAM があることを推奨します。

.. tabs::

  .. tab:: Python

    **MLC LLM をインストール**。:ref:`MLC LLM <install-mlc-packages>` は pip で入手できます。
    分離された conda 仮想環境（conda virtual environment）にインストールすることを常に推奨します。

    **Python でチャット補完（chat completion）を実行**。以下の Python スクリプトは、MLC LLM の Python API を示します。

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

    .. Todo: link the colab notebook when ready:

    **ドキュメントとチュートリアル**。Python API のリファレンスとチュートリアルは :ref:`オンラインで利用可能 <deploy-python-engine>` です。

    .. figure:: https://raw.githubusercontent.com/mlc-ai/web-data/main/images/mlc-llm/tutorials/python-engine-api.jpg
      :width: 600
      :align: center

      MLC LLM Python API

  .. tab:: REST Server

    **MLC LLM をインストール**。:ref:`MLC LLM <install-mlc-packages>` は pip で入手できます。
    分離された conda 仮想環境（conda virtual environment）にインストールすることを常に推奨します。

    **REST サーバーを起動**。コマンドラインから次のコマンドを実行して ``http://127.0.0.1:8000`` に REST サーバーを起動します。

    .. code:: shell

      mlc_llm serve HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC

    **サーバーへリクエストを送信**。サーバーの準備ができたら（``INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`` と表示されたら）、
    新しいシェルを開き、以下のコマンドでリクエストを送信します。

    .. code:: shell

      curl -X POST \
        -H "Content-Type: application/json" \
        -d '{
              "model": "HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC",
              "messages": [
                  {"role": "user", "content": "Hello! Our project is MLC LLM. What is the name of our project?"}
              ]
        }' \
        http://127.0.0.1:8000/v1/chat/completions

    **ドキュメントとチュートリアル**。REST API のリファレンスとチュートリアルは :ref:`deploy-rest-api` を参照してください。
    REST API は OpenAI API を完全にサポートしています。

    .. figure:: https://raw.githubusercontent.com/mlc-ai/web-data/main/images/mlc-llm/tutorials/python-serve-request.jpg
      :width: 600
      :align: center

      Send HTTP request to REST server in MLC LLM

  .. tab:: Command Line

    **MLC LLM をインストール**。:ref:`MLC LLM <install-mlc-packages>` は pip で入手できます。
    分離された conda 仮想環境（conda virtual environment）にインストールすることを常に推奨します。

    Windows/Linux ユーザーは、最新の :ref:`Vulkan ドライバ <vulkan_driver>` をインストールしていることを確認してください。

    **コマンドラインで実行**。

    .. code:: bash

      mlc_llm chat HF://mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC


    Windows/Linux/Steam Deck で Vulkan を使いたい場合は、
    Vulkan が見つからない問題を避けるため、conda で必要な Vulkan ローダー（loader）依存関係を
    インストールすることを推奨します。

    .. code:: bash

      conda install -c conda-forge gcc libvulkan-loader


  .. tab:: Web Browser

    `WebLLM <https://webllm.mlc.ai/#chat-demo>`__。MLC LLM は WebGPU と WebAssembly 用の高性能コードを生成するため、
    サーバーリソースなしでウェブブラウザ上で LLM をローカル実行できます。

    **事前量子化（pre-quantized）重みのダウンロード**。この手順は WebLLM 内で完結します。

    **事前コンパイル済みモデルライブラリのダウンロード**。WebLLM は実行用 WebGPU コードを自動的にダウンロードします。

    **ブラウザ互換性の確認**。最新の Google Chrome には WebGPU ランタイムが搭載されており、
    `WebGPU Report <https://webgpureport.org/>`__ はブラウザの WebGPU 対応状況を確認するための有用なツールです。

    .. figure:: https://blog.mlc.ai/img/redpajama/web.gif
      :width: 300
      :align: center

      MLC LLM on Web

  .. tab:: iOS

    **MLC Chat iOS をインストール**。App Store で入手できます：

    .. image:: https://developer.apple.com/assets/elements/badges/download-on-the-app-store.svg
      :width: 135
      :target: https://apps.apple.com/us/app/mlc-chat/id6448482937

    |

    **注意（Note）**。大きなモデルほど VRAM を多く消費するため、まずは小さいモデルから試してください。

    **チュートリアルとソースコード**。iOS アプリのソースコードは完全に `オープンソース <https://github.com/mlc-ai/mlc-llm/tree/main/ios>`__ で、
    ドキュメントに :ref:`チュートリアル <deploy-ios>` が含まれています。

    .. figure:: https://blog.mlc.ai/img/redpajama/ios.gif
      :width: 300
      :align: center

      MLC Chat on iOS

  .. tab:: Android

    **MLC Chat Android をインストール**。APK としてプリビルド（prebuilt）が提供されています：

    .. image:: https://seeklogo.com/images/D/download-android-apk-badge-logo-D074C6882B-seeklogo.com.png
      :width: 135
      :target: https://github.com/mlc-ai/binary-mlc-llm-libs/releases/download/Android-09262024/mlc-chat.apk

    |

    **注意（Note）**。大きなモデルほど VRAM を多く消費するため、まずは小さいモデルから試してください。
    デモは以下の端末でテストされています。

    - Samsung S23 with Snapdragon 8 Gen 2 chip
    - Redmi Note 12 Pro with Snapdragon 685
    - Google Pixel phones

    **チュートリアルとソースコード**。Android アプリのソースコードは完全に `オープンソース <https://github.com/mlc-ai/mlc-llm/tree/main/android>`__ で、
    ドキュメントに :ref:`チュートリアル <deploy-android>` が含まれています。

    .. figure:: https://blog.mlc.ai/img/android/android-recording.gif
      :width: 300
      :align: center

      MLC LLM on Android


次にやること（What to Do Next）
--------------------------------

- MLC LLM の全体的なワークフロー紹介は :ref:`introduction-to-mlc-llm` を参照してください。
- ユースケースに応じて、API ドキュメントとチュートリアルの各ページを参照してください。

  - :ref:`webllm-runtime`
  - :ref:`deploy-rest-api`
  - :ref:`deploy-cli`
  - :ref:`deploy-python-engine`
  - :ref:`deploy-ios`
  - :ref:`deploy-android`
  - :ref:`deploy-ide-integration`

- 独自モデルを実行したい場合は :ref:`convert-weights-via-MLC` を参照してください。
- Web/iOS/Android へのデプロイやモデル最適化の制御を行いたい場合は :ref:`compile-model-libraries` を参照してください。
- 問題報告や質問は `GitHub リポジトリ <https://github.com/mlc-ai/mlc-llm/issues>`_ に新しい Issue を作成してください。
