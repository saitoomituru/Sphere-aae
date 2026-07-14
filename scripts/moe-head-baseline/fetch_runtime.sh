#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
runtime_version="b9637"
archive_name="llama-${runtime_version}-bin-macos-x64.tar.gz"
archive_sha256="71743f8db0958e7c266cceb7add7b16aa418a964667e471094aa6ae65b9c8298"
download_url="https://github.com/ggml-org/llama.cpp/releases/download/${runtime_version}/${archive_name}"
artifact_root="${repo_root}/build/moe-head-baseline/runtime/${runtime_version}"
archive_path="${artifact_root}/${archive_name}"
extract_root="${artifact_root}/extracted"

mkdir -p "${artifact_root}" "${extract_root}"

if [[ ! -f "${archive_path}" ]]; then
  echo "公式llama.cpp ${runtime_version} macOS x86_64配布物を取得します。"
  curl -L --fail --retry 3 --output "${archive_path}" "${download_url}"
else
  echo "既存archiveを検証します: ${archive_path}"
fi

actual_sha256="$(shasum -a 256 "${archive_path}" | awk '{print $1}')"
if [[ "${actual_sha256}" != "${archive_sha256}" ]]; then
  echo "SHA256不一致: expected=${archive_sha256} actual=${actual_sha256}" >&2
  echo "不一致archiveは自動削除しません。内容を確認してください。" >&2
  exit 1
fi

tar -xzf "${archive_path}" -C "${extract_root}"

server_path="$(find "${extract_root}" -type f -name llama-server -perm -111 | head -1)"
cli_path="$(find "${extract_root}" -type f -name llama-cli -perm -111 | head -1)"
bench_path="$(find "${extract_root}" -type f -name llama-bench -perm -111 | head -1)"

if [[ -z "${server_path}" || -z "${cli_path}" || -z "${bench_path}" ]]; then
  echo "必要な実行fileを配布物から発見できません。" >&2
  exit 1
fi

echo "runtime_version=${runtime_version}"
echo "archive_sha256=${actual_sha256}"
echo "server_path=${server_path}"
echo "cli_path=${cli_path}"
echo "bench_path=${bench_path}"
file "${server_path}"
"${server_path}" --version
