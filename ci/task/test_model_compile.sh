#!/bin/bash
set -eo pipefail
set -x
: ${NUM_THREADS:=$(nproc)}
: ${WORKSPACE_CWD:=$(pwd)}
: ${GPU:="cpu"}

pip install --force-reinstall wheels/*.whl

if [[ ${GPU} == cuda* ]]; then
    TARGET=cuda
    pip install --pre -U --no-index -f https://sphere_aae.ai/wheels sphere-aae-nightly-cu128
    export LD_LIBRARY_PATH=/usr/local/cuda/compat/:$LD_LIBRARY_PATH
elif [[ ${GPU} == rocm* ]]; then
    TARGET=rocm
    pip install --pre -U --no-index -f https://sphere_aae.ai/wheels sphere-aae-nightly-rocm57
elif [[ ${GPU} == metal ]]; then
    TARGET=metal
    pip install --pre -U --force-reinstall -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu
elif [[ ${GPU} == wasm* ]]; then
    TARGET=wasm
    # Clone a copy a tvm source code to build tvm web runtime
    git clone https://github.com/sphere-aae/relax.git /tmp/tvm --recursive
    export TVM_SOURCE_DIR=/tmp/tvm
    # Pip install tvm so that `import tvm` in Python works
    pip install --pre -U --no-index -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu
    export TVM_HOME=${TVM_SOURCE_DIR}
    export SPHERE_AAE_SOURCE_DIR=$(pwd)
    cd $TVM_SOURCE_DIR/web/ && make -j${NUM_THREADS} && cd -
    cd $SPHERE_AAE_SOURCE_DIR/web/ && make -j${NUM_THREADS} && cd -
elif [[ ${GPU} == ios ]]; then
    TARGET=ios
    pip install --pre -U --force-reinstall -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu
elif [[ ${GPU} == android* ]]; then
    TARGET=android
    pip install --pre -U --no-index -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu
else
    TARGET=vulkan
    pip install --pre -U --no-index -f https://sphere_aae.ai/wheels sphere-aae-nightly-cpu
fi

python tests/python/integration/test_model_compile.py $TARGET $NUM_THREADS
