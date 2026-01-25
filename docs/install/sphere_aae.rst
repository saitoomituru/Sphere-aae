.. _install-sphere-aae-packages:

Install Astro Agent Edge (AAE) Python Package
==============================

.. contents:: Table of Contents
    :local:
    :depth: 2

Astro Agent Edge (AAE) Python Package can be installed directly from a prebuilt developer package, or built from source.

Option 1. Prebuilt Package
--------------------------

We provide nightly built pip wheels for Sphere-aae via pip.
Select your operating system/compute platform and run the command in your terminal:

.. note::
    ❗ Whenever using Python, it is highly recommended to use **conda** to manage an isolated Python environment to avoid missing dependencies, incompatible versions, and package conflicts.
    Please make sure your conda environment has Python and pip installed.

.. tabs::

    .. tab:: Linux

        .. tabs::

            .. tab:: CPU

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu sphere-aae-nightly-cpu

            .. tab:: CUDA 12.8

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-cu128 sphere-aae-nightly-cu128

            .. tab:: CUDA 13.0

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-cu130 sphere-aae-nightly-cu130

            .. tab:: ROCm 6.1

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-rocm61 sphere-aae-nightly-rocm61

            .. tab:: ROCm 6.2

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-rocm62 sphere-aae-nightly-rocm62

            .. tab:: Vulkan

                Supported in all Linux packages. Checkout the following instructions
                to install the latest vulkan loader to avoid vulkan not found issue.

                .. code-block:: bash

                    conda install -c conda-forge gcc libvulkan-loader

        .. note::
            We need git-lfs in the system, you can install it via

            .. code-block:: bash

                conda install -c conda-forge git-lfs

            If encountering issues with GLIBC not found, please install the latest glibc in conda:

            .. code-block:: bash

                conda install -c conda-forge libstdcxx-ng

            Besides, we would recommend using Python 3.13; so if you are creating a new environment,
            you could use the following command:

            .. code-block:: bash

                conda create --name sphere-aae-prebuilt  python=3.13

    .. tab:: macOS

        .. tabs::

            .. tab:: CPU + Metal

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu sphere-aae-nightly-cpu

        .. note::

            Always check if conda is installed properly in macOS using the command below:

            .. code-block:: bash

                conda info | grep platform

            It should return "osx-64" for Mac with Intel chip, and "osx-arm64" for Mac with Apple chip.
            We need git-lfs in the system, you can install it via

            .. code-block:: bash

                conda install -c conda-forge git-lfs

    .. tab:: Windows

        .. tabs::

            .. tab:: CPU + Vulkan

                .. code-block:: bash

                    conda activate your-environment
                    python -m pip install --pre -U -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu sphere-aae-nightly-cpu

        .. note::
            Please make sure your conda environment comes with python and pip.
            Make sure you also install the following packages,
            vulkan loader, clang, git and git-lfs to enable proper automatic download
            and jit compilation.

            .. code-block:: bash

                conda install -c conda-forge clang libvulkan-loader git-lfs git

            If encountering the error below:

            .. code-block:: bash

                FileNotFoundError: Could not find module 'path\to\site-packages\tvm\tvm.dll' (or one of its dependencies). Try using the full path with constructor syntax.

            It is likely `zstd`, a dependency to LLVM, was missing. Please use the command below to get it installed:

            .. code-block:: bash

                conda install zstd


Then you can verify installation in command line:

.. code-block:: bash

    python -c "import sphere_aae; print(sphere_aae)"
    # Prints out: <module 'sphere_aae' from '/path-to-env/lib/python3.13/site-packages/sphere_aae/__init__.py'>

|

.. _aaechat_build_from_source:

Option 2. Build from Source
---------------------------

We also provide options to build sphere-aae runtime libraries ``sphere_aae`` from source.
This step is useful when you want to make modification or obtain a specific version of sphere-aae runtime.


**Step 1. Set up build dependency.** To build from source, you need to ensure that the following build dependencies are satisfied:

* CMake >= 3.24
* Git
* `Rust and Cargo <https://www.rust-lang.org/tools/install>`_, required by Hugging Face's tokenizer
* One of the GPU runtimes:

    * CUDA >= 11.8 (NVIDIA GPUs)
    * Metal (Apple GPUs)
    * Vulkan (NVIDIA, AMD, Intel GPUs)

.. code-block:: bash
    :caption: Set up build dependencies in Conda

    # make sure to start with a fresh environment
    conda env remove -n sphere-aae-chat-venv
    # create the conda environment with build dependency
    conda create -n sphere-aae-chat-venv -c conda-forge \
        "cmake>=3.24" \
        rust \
        git \
        python=3.13
    # enter the build environment
    conda activate sphere-aae-chat-venv

.. note::
    For runtime, :doc:`TVM </install/tvm>` compiler is not a dependency for SphereAaeChat CLI or Python API. Only TVM's runtime is required, which is automatically included in `3rdparty/tvm <https://github.com/sphere-aae/sphere-aae/tree/main/3rdparty>`_.
    However, if you would like to compile your own models, you need to follow :doc:`TVM </install/tvm>`.

**Step 2. Configure and build.** A standard git-based workflow is recommended to download Astro Agent Edge (AAE), after which you can specify build requirements with our lightweight config generation tool:

.. code-block:: bash
    :caption: Configure and build

    # clone from GitHub
    git clone --recursive https://github.com/sphere-aae/sphere-aae.git && cd sphere-aae/
    # create build directory
    mkdir -p build && cd build
    # generate build configuration
    python ../cmake/gen_cmake_config.py
    # build sphere_aae libraries
    cmake .. && make -j $(nproc) && cd ..

**Step 3. Install via Python.** We recommend that you install ``sphere_aae`` as a Python package, giving you
access to ``sphere_aae.compile``, ``sphere_aae.SphereAaeEngine``, and the CLI.
There are two ways to do so:

    .. tabs ::

       .. code-tab :: bash Install via environment variable

          export SPHERE_AAE_SOURCE_DIR=/path-to-sphere-aae
          export PYTHONPATH=$SPHERE_AAE_SOURCE_DIR/python:$PYTHONPATH
          alias sphere_aae="python -m sphere_aae"

       .. code-tab :: bash Install via pip local project

          conda activate your-own-env
          which python # make sure python is installed, expected output: path_to_conda/envs/your-own-env/bin/python
          cd /path-to-sphere-aae/python
          pip install -e .

**Step 4. Validate installation.** You may validate if MLC libarires and sphere_aae CLI is compiled successfully using the following command:

.. code-block:: bash
    :caption: Validate installation

    # expected to see `libsphere_aae.so` and `libtvm_runtime.so`
    ls -l ./build/
    # expected to see help message
    sphere_aae chat -h

Finally, you can verify installation in command line. You should see the path you used to build from source with:

.. code:: bash

   python -c "import sphere_aae; print(sphere_aae)"
