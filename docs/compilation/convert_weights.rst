.. _convert-weights-via-AAE:

Convert Model Weights
=====================

To run a model with Astro Agent Edge (AAE),
we need to convert model weights into MLC format (e.g. `RedPajama-INCITE-Chat-3B-v1-q4f16_1-AAE <https://huggingface.co/sphere-aae/RedPajama-INCITE-Chat-3B-v1-q4f16_1-AAE/tree/main>`_.)
This page walks us through the process of adding a model variant with ``sphere_aae convert_weight``, which
takes a huggingface model as input and converts/quantizes into MLC-compatible weights.

Specifically, we add RedPjama-INCITE-**Instruct**-3B-v1, while MLC already
provides a model library for RedPjama-INCITE-**Chat**-3B-v1, which we can reuse.

This can be extended to, e.g.:

- Add ``OpenHermes-Mistral`` when MLC already supports Mistral
- Add ``Llama-2-uncensored`` when MLC already supports Llama-2

.. note::
    Before you proceed, make sure you followed :ref:`install-tvm`, a required
    backend to compile models with Astro Agent Edge (AAE).

    Please also follow the instructions in :ref:`deploy-cli` / :ref:`deploy-python-engine` to obtain
    the CLI app / Python API that can be used to chat with the compiled model.


.. contents:: Table of Contents
    :depth: 1
    :local:

.. _verify_installation_for_compile:

1. Verify installation
----------------------

**Step 1. Verify sphere_aae**

We use the python package ``sphere_aae`` to compile models. This can be installed by
following :ref:`install-sphere-aae-packages`, either by building from source, or by
installing the prebuilt package. Verify ``sphere_aae`` installation in command line via:

.. code:: bash

    $ sphere_aae --help
    # You should see help information with this line
    usage: Astro Agent Edge (AAE) Command Line Interface. [-h] {compile,convert_weight,gen_config}

.. note::
    If it runs into error ``command not found: sphere_aae``, try ``python -m sphere_aae --help``.

**Step 2. Verify TVM**

To compile models, you also need to follow :ref:`install-tvm`.
Here we verify ``tvm`` quickly with command line (for full verification, see :ref:`tvm-validate`):

.. code:: bash

    $ python -c "import tvm; print(tvm.__file__)"
    /some-path/lib/python3.13/site-packages/tvm/__init__.py


1. Clone from HF and convert_weight
-----------------------------------

You can be under the sphere-aae repo, or your own working directory. Note that all platforms
can share the same compiled/quantized weights. See :ref:`compile-command-specification`
for specification of ``convert_weight``.

.. code:: shell

    # Create directory
    mkdir -p dist/models && cd dist/models
    # Clone HF weights
    git lfs install
    git clone https://huggingface.co/togethercomputer/RedPajama-INCITE-Instruct-3B-v1
    cd ../..
    # Convert weight
    sphere_aae convert_weight ./dist/models/RedPajama-INCITE-Instruct-3B-v1/ \
        --quantization q4f16_1 \
        -o dist/RedPajama-INCITE-Instruct-3B-v1-q4f16_1-AAE

.. _generate_sphere_aae_chat_config:

2. Generate MLC Chat Config
---------------------------

Use ``sphere_aae gen_config`` to generate ``sphere-aae-chat-config.json`` and process tokenizers.
See :ref:`compile-command-specification` for specification of ``gen_config``.

.. code:: shell

    sphere_aae gen_config ./dist/models/RedPajama-INCITE-Instruct-3B-v1/ \
        --quantization q4f16_1 --conv-template redpajama_chat \
        -o dist/RedPajama-INCITE-Instruct-3B-v1-q4f16_1-AAE/


.. note::
    The file ``sphere-aae-chat-config.json`` is crucial in both model compilation
    and runtime chatting. Here we only care about the latter case.

    You can **optionally** customize
    ``dist/RedPajama-INCITE-Instruct-3B-v1-q4f16_1-AAE/sphere-aae-chat-config.json`` (checkout :ref:`configure-sphere-aae-chat-json` for more detailed instructions).
    You can also simply use the default configuration.

    `conversation_template <https://github.com/sphere-aae/sphere-aae/blob/main/python/sphere_aae/conversation_template>`__
    directory contains a full list of conversation templates that MLC provides. If the model you are adding
    requires a new conversation template, you would need to add your own.
    Follow `this PR <https://github.com/sphere-aae/sphere-aae/pull/2163>`__ as an example. However,
    adding your own template would require you :ref:`build sphere_aae from source <aaechat_build_from_source>` in order for it
    to be recognized by the runtime.

By now, you should have the following files.

.. code:: shell

    ~/sphere-aae > ls dist/RedPajama-INCITE-Instruct-3B-v1-q4f16_1-AAE
        sphere-aae-chat-config.json                             # ===> the chat config
        tensor-cache.json                               # ===> the model weight info
        params_shard_0.bin                               # ===> the model weights
        params_shard_1.bin
        ...
        tokenizer.json                                   # ===> the tokenizer files
        tokenizer_config.json

.. _distribute-compiled-models:

(Optional) 3. Upload weights to HF
----------------------------------

Optionally, you can upload what we have to huggingface.

.. code:: shell

    # First, please create a repository on Hugging Face.
    # With the repository created, run
    git lfs install
    git clone https://huggingface.co/my-huggingface-account/my-redpajama3b-weight-huggingface-repo
    cd my-redpajama3b-weight-huggingface-repo
    cp path/to/sphere-aae/dist/RedPajama-INCITE-Instruct-3B-v1-q4f16_1-AAE/* .
    git add . && git commit -m "Add redpajama-3b instruct model weights"
    git push origin main

This would result in something like `RedPajama-INCITE-Chat-3B-v1-q4f16_1-AAE
<https://huggingface.co/sphere-aae/RedPajama-INCITE-Chat-3B-v1-q4f16_1-AAE/tree/main>`_, but
for **Instruct** instead of **Chat**.

Good job, you have successfully distributed the model you compiled.
Next, we will talk about how we can consume the model weights in applications.

Download the Distributed Models
-------------------------------

You can now use the existing sphere-aae tools such as chat/serve/package with the converted weights.

.. code:: shell

    sphere_aae chat HF://my-huggingface-account/my-redpajama3b-weight-huggingface-repo
