#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

python_bin="${MOE_BASELINE_PYTHON:-/usr/local/bin/python3.12}"
runtime_release="b9637"
runtime_archive="${repo_root}/build/moe-head-baseline/runtime/${runtime_release}/llama-${runtime_release}-bin-macos-x64.tar.gz"
server_path="${repo_root}/build/moe-head-baseline/runtime/${runtime_release}/extracted/llama-${runtime_release}/llama-server"
model_revision="08d5a8a9741dd5c1a95d2d39e25253226aa1464e"
model_path="${repo_root}/build/moe-head-baseline/models/granite-4.0-h-tiny/${model_revision}/granite-4.0-h-tiny-Q4_K_M.gguf"
fixture_path="${repo_root}/scripts/moe-head-baseline/fixtures/conversations.json"

runtime_archive_sha256="71743f8db0958e7c266cceb7add7b16aa418a964667e471094aa6ae65b9c8298"
server_sha256="d762020bad249d1c74bb6883b7cee178db8ebb48e1872b626280dd1eebb07c39"
model_sha256="5a38b08c441ae1adbafb1d2b8a7167e0d48734d83af68b268cefea1eec553dcd"
model_size_bytes="4230976352"

host="127.0.0.1"
port="${MOE_BASELINE_PORT:-18080}"
thermal_limit="${MOE_BASELINE_MAX_GPU_TEMP_C:-75}"
run_id="$(date -u +%Y%m%dT%H%M%SZ)-upstream-chat-p$$"
started_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
run_dir="${repo_root}/note/moe-head-baseline/runs/${run_id}"
raw_dir="${repo_root}/build/moe-head-baseline/run-raw/${run_id}"
preflight_raw="${raw_dir}/preflight.json"

if [[ ! -x "${python_bin}" ]]; then
  echo "停止: Python 3.12が見つかりません: ${python_bin}" >&2
  exit 2
fi

mkdir -p "${raw_dir}"

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
  "${python_bin}" scripts/moe-head-baseline/summarize_upstream.py \
    --run-dir "${run_dir}" \
    --git-commit "$(git rev-parse HEAD)" \
    --started-utc "${started_utc}" \
    --thermal-limit-c "${thermal_limit}" \
    --chat-status 98 \
    --guard-status 98 \
    --process-monitor-status 98 \
    --server-status 98
  preflight_summary_status=$?
  set -e
  if [[ -f "${run_dir}/REPORT.md" ]]; then
    echo "preflight FAILを保存しました: note/moe-head-baseline/runs/${run_id}/REPORT.md" >&2
  else
    echo "preflight FAILに加えてreport生成も失敗しました: summary=${preflight_summary_status}" >&2
  fi
  exit "${preflight_status}"
fi

mkdir -p "${run_dir}/chat"
cp "${preflight_raw}" "${run_dir}/preflight.json"

events_log="${run_dir}/events.log"
log_event() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" | tee -a "${events_log}"
}

server_pid=""
guard_pid=""
process_monitor_pid=""
chat_status=99
guard_status=99
process_monitor_status=99
server_status=99
shutdown_requested=false
server_forced_kill=false

server_process_state() {
  ps -o state= -p "${server_pid}" 2>/dev/null | tr -d '[:space:]'
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

stop_monitor_process() {
  local pid="$1"
  local child_status
  for _ in {1..5}; do
    if ! pid_running "${pid}"; then
      break
    fi
    sleep 1
  done
  if pid_running "${pid}"; then
    kill -TERM "${pid}" 2>/dev/null
    for _ in {1..2}; do
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

finalize() {
  local initial_status=$?
  trap - EXIT INT TERM
  set +eu

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
  if [[ -n "${guard_pid}" ]]; then
    stop_monitor_process "${guard_pid}"
    guard_status=$?
  fi
  if [[ -n "${process_monitor_pid}" ]]; then
    stop_monitor_process "${process_monitor_pid}"
    process_monitor_status=$?
  fi

  for raw_log in server-console.log server.log; do
    if [[ -f "${raw_dir}/${raw_log}" ]]; then
      sed \
        -e "s#${repo_root}#<REPO_ROOT>#g" \
        -e "s#${HOME}#<HOME>#g" \
        -e 's/[[:space:]]*$//' \
        "${raw_dir}/${raw_log}" > "${run_dir}/${raw_log}"
    fi
  done

  local summary_flags=(--server-status "${server_status}")
  if [[ "${shutdown_requested}" == true ]]; then
    summary_flags+=(--shutdown-requested)
  fi
  if [[ "${server_forced_kill}" == true ]]; then
    summary_flags+=(--server-forced-kill)
  fi

  "${python_bin}" scripts/moe-head-baseline/summarize_upstream.py \
    --run-dir "${run_dir}" \
    --git-commit "$(git rev-parse HEAD)" \
    --started-utc "${started_utc}" \
    --thermal-limit-c "${thermal_limit}" \
    --chat-status "${chat_status}" \
    --guard-status "${guard_status}" \
    --process-monitor-status "${process_monitor_status}" \
    "${summary_flags[@]}"
  local summary_status=$?

  log_event "report生成完了: note/moe-head-baseline/runs/${run_id}/REPORT.md"
  if [[ "${initial_status}" != "0" ]]; then
    exit "${initial_status}"
  fi
  exit "${summary_status}"
}
trap finalize EXIT

log_event "上流MoE baseline開始（FAMなし、HEADなし、CPU-only）"
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
  --log-file "${raw_dir}/server.log" \
  > "${raw_dir}/server-console.log" 2>&1 &
server_pid=$!

"${python_bin}" scripts/coreml/monitor_amd_gpu.py \
  --watch-pid "${server_pid}" \
  --max-temperature-c "${thermal_limit}" \
  --max-samples 3600 \
  --require-telemetry \
  --fail-on-sample-limit \
  --output "${run_dir}/telemetry-gpu.jsonl" &
guard_pid=$!

"${python_bin}" scripts/moe-head-baseline/monitor_process.py \
  --pid "${server_pid}" \
  --max-samples 3600 \
  --output "${run_dir}/telemetry-process.jsonl" &
process_monitor_pid=$!

set +e
"${python_bin}" scripts/moe-head-baseline/run_chat_cases.py \
  --base-url "http://${host}:${port}" \
  --server-pid "${server_pid}" \
  --fixture "${fixture_path}" \
  --output-dir "${run_dir}/chat" \
  --health-timeout-seconds 600 \
  --request-timeout-seconds 300
chat_status=$?
set -e

if [[ "${chat_status}" == "0" ]]; then
  log_event "全会話case完了"
else
  log_event "会話case失敗: exit=${chat_status}"
fi
exit "${chat_status}"
