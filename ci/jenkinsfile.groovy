// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

run_cpu = "bash ci/bash.sh sphereaaedev/ci-cpu:26d65cc -e GPU cpu -e SPHERE_AAE_CI_SETUP_DEPS 1"
run_cuda = "bash ci/bash.sh sphereaaedev/ci-cu128:26d65cc -e GPU cuda-12.8 -e SPHERE_AAE_CI_SETUP_DEPS 1"
// run_rocm = "bash ci/bash.sh sphereaaedev/ci-rocm57:26d65cc -e GPU rocm-5.7 -e SPHERE_AAE_CI_SETUP_DEPS 1"

pkg_cpu = "bash ci/bash.sh sphereaaedev/package-rocm61:519d0b3 -e GPU cpu -e SPHERE_AAE_CI_SETUP_DEPS 1"
pkg_cuda = "bash ci/bash.sh sphereaaedev/package-cu128:519d0b3 -e GPU cuda-12.8 -e SPHERE_AAE_CI_SETUP_DEPS 1"
pkg_rocm = "bash ci/bash.sh sphereaaedev/package-rocm61:519d0b3 -e GPU rocm-6.1 -e SPHERE_AAE_CI_SETUP_DEPS 1"


def per_exec_ws(folder) {
  return "workspace/exec_${env.EXECUTOR_NUMBER}/" + folder
}

def pack_lib(name, libs) {
  sh """
     echo "Packing ${libs} into ${name}"
     echo ${libs} | sed -e 's/,/ /g' | xargs md5sum
     """
  stash includes: libs, name: name
}

def unpack_lib(name, libs) {
  unstash name
  sh """
     echo "Unpacked ${libs} from ${name}"
     echo ${libs} | sed -e 's/,/ /g' | xargs md5sum
     """
}

def init_git(submodule = false) {
  cleanWs()
  // add retry in case checkout timeouts
  retry(5) {
    checkout scm
  }
  if (submodule) {
    retry(5) {
      timeout(time: 10, unit: 'MINUTES') {
        sh(script: 'git submodule update --init --recursive -f', label: 'Update git submodules')
      }
    }
  }
}

stage('Lint') {
  parallel(
    'isort': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-lint-isort')) {
          init_git()
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${run_cpu} conda env export --name ci-lint", label: 'Checkout version')
          sh(script: "${run_cpu} -j 1 conda run -n ci-lint ci/task/isort.sh", label: 'Lint')
        }
      }
    },
    'black': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-lint-black')) {
          init_git()
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${run_cpu} conda env export --name ci-lint", label: 'Checkout version')
          sh(script: "${run_cpu} -j 1 conda run -n ci-lint ci/task/black.sh", label: 'Lint')
        }
      }
    },
    'mypy': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-lint-mypy')) {
          init_git()
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${run_cpu} conda env export --name ci-lint", label: 'Checkout version')
          sh(script: "${run_cpu} -j 1 conda run -n ci-lint ci/task/mypy.sh", label: 'Lint')
        }
      }
    },
    'pylint': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-lint-pylint')) {
          init_git()
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${run_cpu} conda env export --name ci-lint", label: 'Checkout version')
          sh(script: "${run_cpu} -j 4 conda run -n ci-lint ci/task/pylint.sh", label: 'Lint')
        }
      }
    },
    'clang-format': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-lint-clang-format')) {
          init_git()
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${run_cpu} conda env export --name ci-lint", label: 'Checkout version')
          sh(script: "${run_cpu} -j 1 conda run -n ci-lint ci/task/clang-format.sh", label: 'Lint')
        }
      }
    },
  )
}

stage('Build') {
  parallel(
    'CUDA': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-build-cuda')) {
          init_git(true)
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${pkg_cuda} conda env export --name py312", label: 'Checkout version')
          sh(script: "${pkg_cuda} -j 8 -v \$HOME/.ccache /ccache conda run -n py312 ./ci/task/build_lib.sh", label: 'Build Astro Agent Edge (AAE) runtime')
          sh(script: "${pkg_cuda} -j 1 conda run -n py312 ./ci/task/build_clean.sh", label: 'Clean up after build')
          sh(script: "ls -alh ./wheels/", label: 'Build artifact')
          pack_lib('sphere_aae_wheel_cuda', 'wheels/*.whl')
        }
      }
    },
    // 'ROCm': {
    //   node('CPU-SMALL') {
    //     ws(per_exec_ws('sphere-aae-build-rocm')) {
    //       init_git(true)
    //       sh(script: "ls -alh", label: 'Show work directory')
    //       sh(script: "${pkg_rocm} conda env export --name py38", label: 'Checkout version')
    //       sh(script: "${pkg_rocm} -j 8 conda run -n py38 ./ci/task/build_lib.sh", label: 'Build Astro Agent Edge (AAE) runtime')
    //       sh(script: "${pkg_rocm} -j 1 conda run -n py38 ./ci/task/build_clean.sh", label: 'Clean up after build')
    //       sh(script: "ls -alh ./wheels/", label: 'Build artifact')
    //       pack_lib('sphere_aae_wheel_rocm', 'wheels/*.whl')
    //     }
    //   }
    // },
    'Metal': {
      node('MAC') {
        ws(per_exec_ws('sphere-aae-build-metal')) {
          init_git(true)
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "conda env export --name sphere-aae-ci", label: 'Checkout version')
          sh(script: "NUM_THREADS=6 GPU=metal conda run -n sphere-aae-ci ./ci/task/build_lib.sh", label: 'Build Astro Agent Edge (AAE) runtime')
          sh(script: "NUM_THREADS=6 GPU=metal conda run -n sphere-aae-ci ./ci/task/build_clean.sh", label: 'Clean up after build')
          sh(script: "ls -alh ./wheels/", label: 'Build artifact')
          pack_lib('sphere_aae_wheel_metal', 'wheels/*.whl')
        }
      }
    },
    'Vulkan': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-build-vulkan')) {
          init_git(true)
          sh(script: "ls -alh", label: 'Show work directory')
          sh(script: "${pkg_cpu} conda env export --name py312", label: 'Checkout version')
          sh(script: "${pkg_cpu} -j 8 conda run -n py312 ./ci/task/build_lib.sh", label: 'Build Astro Agent Edge (AAE) runtime')
          sh(script: "${pkg_cpu} -j 1 conda run -n py312 ./ci/task/build_clean.sh", label: 'Clean up after build')
          sh(script: "ls -alh ./wheels/", label: 'Build artifact')
          pack_lib('sphere_aae_wheel_vulkan', 'wheels/*.whl')
        }
      }
    }
  )
}

stage('Unittest') {
  parallel(
    'CUDA': {
      node('GPU') {
        ws(per_exec_ws('sphere-aae-unittest')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_cuda', 'wheels/*.whl')
          sh(script: "${run_cuda} conda env export --name ci-unittest", label: 'Checkout version')
          sh(script: "${run_cuda} conda run -n ci-unittest ./ci/task/test_unittest.sh", label: 'Testing')
        }
      }
    }
  )
}

stage('Model Compilation') {
  parallel(
    'CUDA': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-compile-cuda')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_cuda', 'wheels/*.whl')
          sh(script: "${run_cuda} conda env export --name ci-unittest", label: 'Checkout version')
          sh(script: "${run_cuda} -j 4 conda run -n ci-unittest ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    },
    // 'ROCm': {
    //   node('CPU-SMALL') {
    //     ws(per_exec_ws('sphere-aae-compile-rocm')) {
    //       init_git(false)
    //       sh(script: "ls -alh", label: 'Show work directory')
    //       unpack_lib('sphere_aae_wheel_rocm', 'wheels/*.whl')
    //       sh(script: "${run_rocm} conda env export --name ci-unittest", label: 'Checkout version')
    //       sh(script: "${run_rocm} -j 4 conda run -n ci-unittest ./ci/task/test_model_compile.sh", label: 'Testing')
    //     }
    //   }
    // },
    'Metal': {
      node('MAC') {
        ws(per_exec_ws('sphere-aae-compile-metal')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_metal', 'wheels/*.whl')
          sh(script: "conda env export --name sphere-aae-ci", label: 'Checkout version')
          sh(script: "NUM_THREADS=6 GPU=metal conda run -n sphere-aae-ci ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    },
    'Vulkan': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-compile-vulkan')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_vulkan', 'wheels/*.whl')
          sh(script: "${run_cpu} conda env export --name ci-unittest", label: 'Checkout version')
          // sh(script: "${run_cpu} -j 4 conda run -n ci-unittest ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    },
    'WASM': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-compile-wasm')) {
          init_git(true)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_vulkan', 'wheels/*.whl')
          sh(script: "${run_cpu} conda env export --name ci-unittest", label: 'Checkout version')
          sh(script: "${run_cpu} -j 8 -e GPU wasm conda run -n ci-unittest ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    },
    'iOS': {
      node('MAC') {
        ws(per_exec_ws('sphere-aae-compile-ios')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_metal', 'wheels/*.whl')
          sh(script: "conda env export --name sphere-aae-ci", label: 'Checkout version')
          sh(script: "NUM_THREADS=6 GPU=ios conda run -n sphere-aae-ci ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    },
    'Android-OpenCL': {
      node('CPU-SMALL') {
        ws(per_exec_ws('sphere-aae-compile-android')) {
          init_git(false)
          sh(script: "ls -alh", label: 'Show work directory')
          unpack_lib('sphere_aae_wheel_vulkan', 'wheels/*.whl')
          sh(script: "${run_cpu} conda env export --name ci-unittest", label: 'Checkout version')
          sh(script: "${run_cpu} -j 4 -e GPU android conda run -n ci-unittest ./ci/task/test_model_compile.sh", label: 'Testing')
        }
      }
    }
  )
}
