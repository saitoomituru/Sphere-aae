#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

python_bin="${MOE_BASELINE_PYTHON:-/usr/local/bin/python3.12}"
coreml_python="${COREML_PYTHON:-${repo_root}/build/venvs/coreml/bin/python}"
runtime_release="b9637"
runtime_archive="${repo_root}/build/moe-head-baseline/runtime/${runtime_release}/llama-${runtime_release}-bin-macos-x64.tar.gz"
server_path="${repo_root}/build/moe-head-baseline/runtime/${runtime_release}/extracted/llama-${runtime_release}/llama-server"
model_revision="08d5a8a9741dd5c1a95d2d39e25253226aa1464e"
model_path="${repo_root}/build/moe-head-baseline/models/granite-4.0-h-tiny/${model_revision}/granite-4.0-h-tiny-Q4_K_M.gguf"
conversation_fixture="${repo_root}/scripts/moe-head-baseline/fixtures/conversations.json"

runtime_archive_sha256="71743f8db0958e7c266cceb7add7b16aa418a964667e471094aa6ae65b9c8298"
server_sha256="d762020bad249d1c74bb6883b7cee178db8ebb48e1872b626280dd1eebb07c39"
model_sha256="5a38b08c441ae1adbafb1d2b8a7167e0d48734d83af68b268cefea1eec553dcd"
model_size_bytes="4230976352"

host="127.0.0.1"
port="${MOE_HEAD_BASELINE_PORT:-18080}"
thermal_limit="${MOE_HEAD_MAX_GPU_TEMP_C:-75}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-head-bypass-p$$"
started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
run_dir="${repo_root}/note/moe-head-baseline/runs/${run_id}"
raw_dir="${repo_root}/build/moe-head-baseline/run-raw/${run_id}"
artifact_root="${repo_root}/build/moe-head-baseline/head-runs/${run_id}"
fixture_dir="${artifact_root}/fixture"
compiled_root="${artifact_root}/compiled"
swift_scratch="${repo_root}/build/moe-head-baseline/head-swift"
head_package="${fixture_dir}/MinimalArbiterZeroB1.mlpackage"
head_fixture="${fixture_dir}/fixture.json"
compiled_model="${compiled_root}/MinimalArbiterZeroB1.mlmodelc"
head_binary="${swift_scratch}/release/moe-head-baseline"
preflight_raw="${raw_dir}/preflight.json"

if [[ ! -x "${python_bin}" ]]; then
  echo "停止: Python 3.12が見つかりません: ${python_bin}" >&2
  exit 2
fi

mkdir -p "${raw_dir}" "${artifact_root}"

set +e
"${python_bin}" scripts/moe-head-baseline/preflight.py \
  --repo-root "${repo_root}" \
  --output "${preflight_raw}" \
  --runtime-archive "${runtime_archive}" \
  --runtime-archive-sha256 "${runtime_archive_sha256}" \
  --server "${server_path}" \
  --server-sha256 "${server_sha256}" \
  --model "${model_path}" \
  --model-size-bytes "${model_size_bytes}" \
  --model-sha256 "${model_sha256}" \
  --maximum-initial-gpu-temperature-c "${thermal_limit}" \
  --host "${host}" \
  --port "${port}"
preflight_status=$?
set -e

if [[ "${preflight_status}" == "0" && ! -s "${preflight_raw}" ]]; then
  preflight_status=97
fi

if [[ "${preflight_status}" != "0" ]]; then
  mkdir -p "${run_dir}"
  if [[ -s "${preflight_raw}" ]]; then
    cp "${preflight_raw}" "${run_dir}/preflight.json"
  fi
  set +e
  "${python_bin}" scripts/moe-head-baseline/summarize_head_bypass.py \
    --run-dir "${run_dir}" \
    --git-commit "$(git rev-parse HEAD)" \
    --started-utc "${started_utc}" \
    --thermal-limit-c "${thermal_limit}" \
    --fixture-build-status 98 --fixture-guard-status 98 \
    --compiler-status 98 --compiler-guard-status 98 \
    --swift-build-status 98 --swift-guard-status 98 \
    --comparison-status 98 --server-guard-status 98 \
    --process-monitor-status 98 --server-status 98 \
    --compiled-model "${compiled_model}" \
    --head-binary "${head_binary}"
  summary_status=$?
  set -e
  if [[ -f "${run_dir}/REPORT.md" ]]; then
    echo "preflight FAILを保存しました: note/moe-head-baseline/runs/${run_id}/REPORT.md" >&2
  else
    echo "preflight FAILに加えてreport生成も失敗しました: summary=${summary_status}" >&2
  fi
  exit "${preflight_status}"
fi

mkdir -p "${run_dir}/head" "${run_dir}/comparison" "${fixture_dir}" "${compiled_root}"
cp "${preflight_raw}" "${run_dir}/preflight.json"

events_file="${run_dir}/events.txt"
log_event() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" | tee -a "${events_file}"
}

fixture_build_status=99
fixture_guard_status=99
compiler_status=99
compiler_guard_status=99
swift_build_status=99
swift_guard_status=99
comparison_status=99
server_guard_status=99
process_monitor_status=99
server_status=99
shutdown_requested=false
server_forced_kill=false
active_pid=""
server_pid=""
server_guard_pid=""
process_monitor_pid=""
last_workload_status=99
last_guard_status=99

sanitize_file() {
  local source="$1"
  local destination="$2"
  if [[ -f "${source}" ]]; then
    sed \
      -e "s#${repo_root}#<REPO_ROOT>#g" \
      -e "s#${HOME}#<HOME>#g" \
      -e 's/[[:space:]]*$//' \
      "${source}" > "${destination}"
  fi
}

pid_running() {
  local pid="$1"
  local state
  if ! kill -0 "${pid}" 2>/dev/null; then
    return 1
  fi
  state="$(ps -o state= -p "${pid}" 2>/dev/null | tr -d '[:space:]')"
  [[ "${state}" != Z* ]]
}

stop_child_process() {
  local pid="$1"
  local graceful_seconds="$2"
  local natural_wait_seconds="${3:-0}"
  local child_status
  for ((index = 0; index < natural_wait_seconds; index += 1)); do
    if ! pid_running "${pid}"; then
      break
    fi
    sleep 1
  done
  if pid_running "${pid}"; then
    kill -TERM "${pid}" 2>/dev/null
    for ((index = 0; index < graceful_seconds; index += 1)); do
      if ! pid_running "${pid}"; then
        break
      fi
      sleep 1
    done
  fi
  if pid_running "${pid}"; then
    kill -KILL "${pid}" 2>/dev/null
    sleep 1
  fi
  if pid_running "${pid}"; then
    return 124
  fi
  wait "${pid}" 2>/dev/null
  child_status=$?
  return "${child_status}"
}

run_guarded_step() {
  local slug="$1"
  shift
  local workload_pid
  log_event "${slug}開始"
  "$@" > "${raw_dir}/${slug}.txt" 2>&1 &
  workload_pid=$!
  active_pid="${workload_pid}"

  set +e
  "${python_bin}" scripts/coreml/monitor_amd_gpu.py \
    --watch-pid "${workload_pid}" \
    --max-temperature-c "${thermal_limit}" \
    --max-samples 600 \
    --require-telemetry \
    --fail-on-sample-limit \
    --output "${run_dir}/telemetry-gpu-${slug}.jsonl"
  last_guard_status=$?
  if [[ "${last_guard_status}" != "0" ]]; then
    stop_child_process "${workload_pid}" 5
    last_workload_status=$?
  else
    wait "${workload_pid}"
    last_workload_status=$?
  fi
  set -e
  active_pid=""

  sanitize_file "${raw_dir}/${slug}.txt" "${run_dir}/${slug}.txt"
  log_event "${slug}終了: workload=${last_workload_status}, guard=${last_guard_status}"
  [[ "${last_workload_status}" == "0" && "${last_guard_status}" == "0" ]]
}

server_process_state() {
  ps -o state= -p "${server_pid}" 2>/dev/null | tr -d '[:space:]'
}

finalize() {
  local initial_status=$?
  trap - EXIT INT TERM
  set +eu

  if [[ -n "${active_pid}" ]]; then
    stop_child_process "${active_pid}" 3
    active_pid=""
  fi

  local current_state=""
  if [[ -n "${server_pid}" ]]; then
    current_state="$(server_process_state)"
  fi
  if [[ -n "${server_pid}" ]] && kill -0 "${server_pid}" 2>/dev/null && [[ "${current_state}" != Z* ]]; then
    shutdown_requested=true
    log_event "llama-serverへSIGTERMを送信"
    kill -TERM "${server_pid}" 2>/dev/null
    for _ in {1..15}; do
      current_state="$(server_process_state)"
      if ! kill -0 "${server_pid}" 2>/dev/null || [[ "${current_state}" == Z* ]]; then
        break
      fi
      sleep 1
    done
    current_state="$(server_process_state)"
    if kill -0 "${server_pid}" 2>/dev/null && [[ "${current_state}" != Z* ]]; then
      server_forced_kill=true
      log_event "SIGTERM停止timeoutのためllama-serverへSIGKILLを送信"
      kill -KILL "${server_pid}" 2>/dev/null
      for _ in {1..5}; do
        current_state="$(server_process_state)"
        if ! kill -0 "${server_pid}" 2>/dev/null || [[ "${current_state}" == Z* ]]; then
          break
        fi
        sleep 1
      done
    fi
  fi
  if [[ -n "${server_pid}" ]]; then
    current_state="$(server_process_state)"
    if ! kill -0 "${server_pid}" 2>/dev/null || [[ "${current_state}" == Z* ]]; then
      wait "${server_pid}" 2>/dev/null
      server_status=$?
    else
      server_status=124
    fi
  fi
  if [[ -n "${server_guard_pid}" ]]; then
    stop_child_process "${server_guard_pid}" 2 5
    server_guard_status=$?
  fi
  if [[ -n "${process_monitor_pid}" ]]; then
    stop_child_process "${process_monitor_pid}" 2 5
    process_monitor_status=$?
  fi

  sanitize_file "${raw_dir}/server-console.txt" "${run_dir}/server-console.txt"
  sanitize_file "${raw_dir}/server.txt" "${run_dir}/server.txt"

  local summary_flags=(--server-status "${server_status}")
  if [[ "${shutdown_requested}" == true ]]; then
    summary_flags+=(--shutdown-requested)
  fi
  if [[ "${server_forced_kill}" == true ]]; then
    summary_flags+=(--server-forced-kill)
  fi

  "${python_bin}" scripts/moe-head-baseline/summarize_head_bypass.py \
    --run-dir "${run_dir}" \
    --git-commit "$(git rev-parse HEAD)" \
    --started-utc "${started_utc}" \
    --thermal-limit-c "${thermal_limit}" \
    --fixture-build-status "${fixture_build_status}" \
    --fixture-guard-status "${fixture_guard_status}" \
    --compiler-status "${compiler_status}" \
    --compiler-guard-status "${compiler_guard_status}" \
    --swift-build-status "${swift_build_status}" \
    --swift-guard-status "${swift_guard_status}" \
    --comparison-status "${comparison_status}" \
    --server-guard-status "${server_guard_status}" \
    --process-monitor-status "${process_monitor_status}" \
    --compiled-model "${compiled_model}" \
    --head-binary "${head_binary}" \
    "${summary_flags[@]}"
  local summary_status=$?

  log_event "report生成完了: note/moe-head-baseline/runs/${run_id}/REPORT.md"
  if [[ "${initial_status}" != "0" ]]; then
    exit "${initial_status}"
  fi
  exit "${summary_status}"
}
trap finalize EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

log_event "MoE HEAD bypass baseline開始（FAMなし、router overrideなし）"

if [[ ! -x "${coreml_python}" ]]; then
  fixture_build_status=127
  log_event "Core ML Python環境がないため停止"
  exit 1
fi

if run_guarded_step build-fixture \
  "${coreml_python}" scripts/coreml/build_fixture.py \
    --batch-size 1 \
    --input-mode zero \
    --output-dir "${fixture_dir}"; then
  :
fi
fixture_build_status="${last_workload_status}"
fixture_guard_status="${last_guard_status}"
if [[ "${fixture_build_status}" != "0" || "${fixture_guard_status}" != "0" ]]; then
  exit 1
fi
cp "${head_fixture}" "${run_dir}/head/fixture.json"
cp "${fixture_dir}/manifest.json" "${run_dir}/head/fixture-manifest.json"

if run_guarded_step compile-model \
  xcrun coremlcompiler compile "${head_package}" "${compiled_root}"; then
  :
fi
compiler_status="${last_workload_status}"
compiler_guard_status="${last_guard_status}"
if [[ "${compiler_status}" != "0" || "${compiler_guard_status}" != "0" || ! -d "${compiled_model}" ]]; then
  [[ "${compiler_status}" == "0" && -d "${compiled_model}" ]] || compiler_status=97
  exit 1
fi

if run_guarded_step swift-build \
  swift build \
    --package-path tests/apple/coreml-smoke \
    --scratch-path "${swift_scratch}" \
    --product moe-head-baseline \
    -c release; then
  :
fi
swift_build_status="${last_workload_status}"
swift_guard_status="${last_guard_status}"
if [[ "${swift_build_status}" != "0" || "${swift_guard_status}" != "0" || ! -x "${head_binary}" ]]; then
  [[ "${swift_build_status}" == "0" && -x "${head_binary}" ]] || swift_build_status=97
  exit 1
fi

log_event "固定MoE runtimeをCPU-onlyで起動"
"${server_path}" \
  --model "${model_path}" \
  --alias granite-4.0-h-tiny-q4km \
  --device none \
  --n-gpu-layers 0 \
  --no-kv-offload \
  --threads 6 \
  --threads-batch 6 \
  --ctx-size 2048 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 1 \
  --jinja \
  --no-cache-prompt \
  --offline \
  --fit off \
  --host "${host}" \
  --port "${port}" \
  --timeout 300 \
  --metrics \
  --log-timestamps \
  --log-file "${raw_dir}/server.txt" \
  > "${raw_dir}/server-console.txt" 2>&1 &
server_pid=$!

"${python_bin}" scripts/coreml/monitor_amd_gpu.py \
  --watch-pid "${server_pid}" \
  --max-temperature-c "${thermal_limit}" \
  --max-samples 3600 \
  --require-telemetry \
  --fail-on-sample-limit \
  --output "${run_dir}/telemetry-gpu-server.jsonl" &
server_guard_pid=$!

"${python_bin}" scripts/moe-head-baseline/monitor_process.py \
  --pid "${server_pid}" \
  --max-samples 3600 \
  --output "${run_dir}/telemetry-process-server.jsonl" &
process_monitor_pid=$!

set +e
"${python_bin}" scripts/moe-head-baseline/run_head_bypass_cases.py \
  --base-url "http://${host}:${port}" \
  --server-pid "${server_pid}" \
  --fixture "${conversation_fixture}" \
  --head-binary "${head_binary}" \
  --head-model "${compiled_model}" \
  --head-fixture "${head_fixture}" \
  --repo-root "${repo_root}" \
  --output-dir "${run_dir}/comparison"
comparison_status=$?
set -e

if [[ "${comparison_status}" == "0" ]]; then
  log_event "A1/A2/HEAD/B比較完了"
else
  log_event "A1/A2/HEAD/B比較失敗: exit=${comparison_status}"
fi
exit "${comparison_status}"
