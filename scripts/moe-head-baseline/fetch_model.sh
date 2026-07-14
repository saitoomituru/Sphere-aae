#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
model_repository="ibm-granite/granite-4.0-h-tiny-GGUF"
model_revision="08d5a8a9741dd5c1a95d2d39e25253226aa1464e"
model_filename="granite-4.0-h-tiny-Q4_K_M.gguf"
model_size_bytes="4230976352"
model_sha256="5a38b08c441ae1adbafb1d2b8a7167e0d48734d83af68b268cefea1eec553dcd"
download_url="https://huggingface.co/${model_repository}/resolve/${model_revision}/${model_filename}?download=true"
artifact_root="${repo_root}/build/moe-head-baseline/models/granite-4.0-h-tiny/${model_revision}"
model_path="${artifact_root}/${model_filename}"
minimum_free_kib=$((40 * 1024 * 1024))

free_kib="$(df -Pk "${repo_root}" | awk 'NR == 2 {print $4}')"
if (( free_kib < minimum_free_kib )); then
  echo "空き容量が40 GiB未満のため取得を停止します。free_kib=${free_kib}" >&2
  exit 1
fi

mkdir -p "${artifact_root}"

echo "IBM公式Granite Q4_K_Mを固定revisionから取得・再開します。"
curl -L --fail --retry 3 --continue-at - --output "${model_path}" "${download_url}"

actual_size_bytes="$(stat -f '%z' "${model_path}")"
if [[ "${actual_size_bytes}" != "${model_size_bytes}" ]]; then
  echo "file size不一致: expected=${model_size_bytes} actual=${actual_size_bytes}" >&2
  echo "不一致fileは自動削除しません。再開可否を確認してください。" >&2
  exit 1
fi

actual_sha256="$(shasum -a 256 "${model_path}" | awk '{print $1}')"
if [[ "${actual_sha256}" != "${model_sha256}" ]]; then
  echo "SHA256不一致: expected=${model_sha256} actual=${actual_sha256}" >&2
  echo "不一致fileは自動削除しません。内容を確認してください。" >&2
  exit 1
fi

echo "model_repository=${model_repository}"
echo "model_revision=${model_revision}"
echo "model_filename=${model_filename}"
echo "model_size_bytes=${actual_size_bytes}"
echo "model_sha256=${actual_sha256}"
