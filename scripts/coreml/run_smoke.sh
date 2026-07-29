#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

python_bin="${COREML_PYTHON:-${repo_root}/build/venvs/coreml/bin/python}"
thermal_limit="${COREML_MAX_GPU_TEMP_C:-80}"
latency_iterations="${COREML_LATENCY_ITERATIONS:-1000}"
throughput_iterations="${COREML_THROUGHPUT_ITERATIONS:-200}"
warmup_iterations="${COREML_WARMUP_ITERATIONS:-20}"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to run: commit and push the working tree first." >&2
  exit 2
fi

upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}')"
if [[ "$(git rev-list --count "${upstream}..HEAD")" != "0" ]]; then
  echo "Refusing to run: HEAD has commits not present in ${upstream}." >&2
  exit 2
fi

if [[ ! -x "${python_bin}" ]]; then
  echo "Core ML Python environment not found: ${python_bin}" >&2
  exit 2
fi

run_id="$(date -u +%Y%m%dT%H%M%SZ)"
run_dir="${repo_root}/logs/coreml/runs/${run_id}"
artifact_root="${repo_root}/build/coreml/${run_id}"
swift_scratch="${repo_root}/build/coreml/swift"
mkdir -p "${run_dir}" "${artifact_root}"

finalize() {
  local exit_status=$?
  trap - EXIT
  /usr/local/bin/python3.12 scripts/coreml/summarize_run.py \
    --run-dir "${run_dir}" \
    --git-commit "$(git rev-parse HEAD)" \
    --thermal-limit-c "${thermal_limit}" || true
  echo "Core ML report: ${run_dir}/REPORT.md"
  exit "${exit_status}"
}
trap finalize EXIT

git rev-parse HEAD > "${run_dir}/git-commit.txt"
sw_vers > "${run_dir}/macos.txt"
xcodebuild -version > "${run_dir}/xcode.txt"
system_profiler SPHardwareDataType SPDisplaysDataType \
  | sed -E '/Serial Number|Hardware UUID|Provisioning UDID/d' \
  > "${run_dir}/hardware.txt"

"${python_bin}" scripts/coreml/build_fixture.py \
  --batch-size 1 --output-dir "${artifact_root}/batch-1" \
  > "${run_dir}/build-batch-1.txt"
"${python_bin}" scripts/coreml/build_fixture.py \
  --batch-size 256 --output-dir "${artifact_root}/batch-256" \
  > "${run_dir}/build-batch-256.txt"

for batch in 1 256; do
  mkdir -p "${artifact_root}/compiled-${batch}"
  xcrun coremlcompiler compile \
    "${artifact_root}/batch-${batch}/MinimalArbiterB${batch}.mlpackage" \
    "${artifact_root}/compiled-${batch}" \
    2>&1 \
    | sed "s#${repo_root}#<REPO_ROOT>#g" \
    > "${run_dir}/compile-batch-${batch}.txt"
done

swift build \
  --package-path tests/apple/coreml-smoke \
  --scratch-path "${swift_scratch}" \
  -c release \
  > "${run_dir}/swift-build.txt" 2>&1
runner="${swift_scratch}/release/coreml-smoke"

run_profile() {
  local profile="$1"
  local batch="$2"
  local compute_units="$3"
  local iterations="$4"
  local slug="${profile}-${compute_units}"

  "${runner}" \
    --model "${artifact_root}/compiled-${batch}/MinimalArbiterB${batch}.mlmodelc" \
    --fixture "${artifact_root}/batch-${batch}/fixture.json" \
    --profile "${profile}" \
    --compute-units "${compute_units}" \
    --warmup "${warmup_iterations}" \
    --iterations "${iterations}" \
    --json-output "${run_dir}/result-${slug}.json" \
    > "${run_dir}/runner-${slug}.txt" 2>&1 &
  local workload_pid=$!

  set +e
  /usr/local/bin/python3.12 scripts/coreml/monitor_amd_gpu.py \
    --watch-pid "${workload_pid}" \
    --max-temperature-c "${thermal_limit}" \
    --output "${run_dir}/telemetry-${slug}.jsonl"
  local guard_status=$?
  wait "${workload_pid}"
  local workload_status=$?
  set -e

  if [[ "${guard_status}" != "0" || "${workload_status}" != "0" ]]; then
    echo "${slug} failed: workload=${workload_status}, guard=${guard_status}" >&2
    return 1
  fi
}

run_profile latency 1 cpuOnly "${latency_iterations}"
run_profile latency 1 cpuAndGPU "${latency_iterations}"
run_profile throughput 256 cpuOnly "${throughput_iterations}"
run_profile throughput 256 cpuAndGPU "${throughput_iterations}"
