#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

export PYTHONPATH="${ROOT_DIR}/python:${ROOT_DIR}/3rdparty/tvm/python:${PYTHONPATH:-}"
export TVM_LIBRARY_PATH="${ROOT_DIR}/build/tvm"

python3 -m pip install -U pip wheel setuptools

TMP_REQUIREMENTS="$(mktemp)"
grep -v "^flashinfer-python" python/requirements.txt > "${TMP_REQUIREMENTS}"
python3 -m pip install -r "${TMP_REQUIREMENTS}"
rm -f "${TMP_REQUIREMENTS}"

python3 -m pip install -r docs/requirements.txt
python3 -m pip install -e 3rdparty/tvm/3rdparty/tvm-ffi
python3 -m pip install psutil scipy pytest

mkdir -p build
cat > build/config.cmake <<'EOF'
set(USE_CUDA OFF)
set(USE_ROCM OFF)
set(USE_VULKAN OFF)
set(USE_OPENCL OFF)
set(USE_METAL OFF)
set(USE_LLVM OFF)
set(BUILD_DUMMY_LIBTVM OFF)
EOF

cmake -S . -B build -G Ninja -DSPHERE_AAE_BUILD_PYTHON_MODULE=ON
cmake --build build

pytest tests/python

make -C docs html
