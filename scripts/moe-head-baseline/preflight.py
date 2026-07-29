#!/usr/bin/env python3
"""MoE baselineの高負荷実行前に、保存状態と実体をfail-closedで検証する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def git_text(repo_root: Path, *arguments: str) -> str:
    result = run(["git", *arguments], repo_root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git commandが失敗しました")
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def read_gpu_telemetry() -> dict[str, Any]:
    result = subprocess.run(
        ["ioreg", "-l", "-w0", "-r", "-k", "PerformanceStatistics"],
        check=False,
        capture_output=True,
        text=True,
    )
    lines = [line for line in result.stdout.splitlines() if '"PerformanceStatistics" =' in line]

    def all_values(key: str) -> list[int]:
        values: list[int] = []
        for line in lines:
            match = re.search(rf'"{re.escape(key)}"=(-?\d+)', line)
            if match:
                values.append(int(match.group(1)))
        return values

    temperatures = all_values("Temperature(C)")
    recoveries = all_values("recoveryCount")
    return {
        "ioreg_returncode": result.returncode,
        "telemetry_available": bool(lines and temperatures),
        "gpu_count_with_temperature": len(temperatures),
        "maximum_temperature_c": max(temperatures) if temperatures else None,
        "recovery_counts": recoveries,
        "cpu_temperature_c": None,
    }


def check_port(host: str, port: int) -> tuple[bool, str | None]:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((host, port))
    except OSError as error:
        return False, str(error)
    finally:
        listener.close()
    return True, None


def relative_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return "<REPO外のpath>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-branch", default="moe-test-edition")
    parser.add_argument("--expected-upstream", default="origin/moe-test-edition")
    parser.add_argument("--runtime-archive", type=Path, required=True)
    parser.add_argument("--runtime-archive-sha256", required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--server-sha256", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-size-bytes", type=int, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--minimum-free-gib", type=int, default=40)
    parser.add_argument("--maximum-initial-gpu-temperature-c", type=int, default=75)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    errors: list[str] = []
    checks: dict[str, Any] = {}

    try:
        branch = git_text(repo_root, "branch", "--show-current")
        upstream = git_text(repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        head = git_text(repo_root, "rev-parse", "HEAD")
        upstream_head = git_text(repo_root, "rev-parse", "@{upstream}")
        status = git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
        checks["git"] = {
            "branch": branch,
            "expected_branch": args.expected_branch,
            "upstream": upstream,
            "expected_upstream": args.expected_upstream,
            "head": head,
            "cached_upstream_head": upstream_head,
            "working_tree_clean": not status,
        }
        if branch != args.expected_branch:
            errors.append(f"branchが想定外です: {branch}")
        if upstream != args.expected_upstream:
            errors.append(f"upstreamが想定外です: {upstream}")
        if status:
            errors.append("作業treeに未保存変更があります")
        if head != upstream_head:
            errors.append("HEADがlocal upstream追跡refと一致しません")

        remote_environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        remote_result = run(
            ["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{args.expected_branch}"],
            repo_root,
            env=remote_environment,
        )
        remote_fields = remote_result.stdout.strip().split()
        remote_head = remote_fields[0] if remote_result.returncode == 0 and remote_fields else None
        checks["git"]["live_remote_checked"] = remote_result.returncode == 0
        checks["git"]["live_remote_head"] = remote_head
        if remote_head is None:
            errors.append("originのlive remote SHAを確認できません")
        elif remote_head != head:
            errors.append("HEADがoriginのlive remote SHAと一致しません")
    except RuntimeError as error:
        checks["git"] = {"error": str(error)}
        errors.append(f"Git保存状態を確認できません: {error}")

    disk = shutil.disk_usage(repo_root)
    minimum_free_bytes = args.minimum_free_gib * 1024**3
    checks["disk"] = {
        "free_bytes": disk.free,
        "minimum_free_bytes": minimum_free_bytes,
        "passed": disk.free >= minimum_free_bytes,
    }
    if disk.free < minimum_free_bytes:
        errors.append(f"空き容量が{args.minimum_free_gib} GiB未満です")

    file_specs = [
        ("runtime_archive", args.runtime_archive, args.runtime_archive_sha256, None),
        ("llama_server", args.server, args.server_sha256, None),
        ("model", args.model, args.model_sha256, args.model_size_bytes),
    ]
    checks["artifacts"] = {}
    for label, path, expected_hash, expected_size in file_specs:
        record: dict[str, Any] = {
            "path": relative_path(path, repo_root),
            "exists": path.is_file(),
            "expected_sha256": expected_hash,
        }
        if path.is_file():
            record["size_bytes"] = path.stat().st_size
            record["actual_sha256"] = sha256_file(path)
            record["sha256_matches"] = record["actual_sha256"] == expected_hash
            if expected_size is not None:
                record["expected_size_bytes"] = expected_size
                record["size_matches"] = record["size_bytes"] == expected_size
        checks["artifacts"][label] = record
        if not record["exists"]:
            errors.append(f"{label}が見つかりません")
        elif not record.get("sha256_matches"):
            errors.append(f"{label}のSHA256が不一致です")
        elif expected_size is not None and not record.get("size_matches"):
            errors.append(f"{label}のfile sizeが不一致です")

    if args.server.is_file():
        file_result = run(["file", str(args.server)], repo_root)
        version_result = run([str(args.server), "--version"], repo_root)
        devices_result = run([str(args.server), "--list-devices"], repo_root)
        device_lines = [line.strip() for line in devices_result.stdout.splitlines() if line.strip()]
        device_text = "\n".join(device_lines)
        cpu_only = (
            devices_result.returncode == 0
            and bool(device_lines)
            and "Accelerate" in device_text
            and not re.search(r"Metal|CUDA|Vulkan|ROCm|SYCL", device_text, re.IGNORECASE)
        )
        architecture_ok = file_result.returncode == 0 and "x86_64" in file_result.stdout
        version_text = (version_result.stdout + version_result.stderr).strip()
        version_ok = version_result.returncode == 0 and "9637" in version_text and "aedb2a5e9" in version_text
        checks["runtime"] = {
            "architecture": "x86_64" if architecture_ok else "確認失敗",
            "architecture_passed": architecture_ok,
            "version": version_text,
            "version_passed": version_ok,
            "devices": device_lines,
            "cpu_only_distribution": cpu_only,
        }
        if not architecture_ok:
            errors.append("llama-serverがx86_64実行fileではありません")
        if not version_ok:
            errors.append("llama-serverのversion/commitが固定値と一致しません")
        if not cpu_only:
            errors.append("llama-serverのdevice構成がAccelerate CPU-onlyではありません")

    telemetry = read_gpu_telemetry()
    initial_temperature = telemetry.get("maximum_temperature_c")
    telemetry["maximum_allowed_temperature_c"] = args.maximum_initial_gpu_temperature_c
    telemetry["passed"] = bool(
        telemetry["telemetry_available"]
        and initial_temperature is not None
        and initial_temperature < args.maximum_initial_gpu_temperature_c
        and telemetry["recovery_counts"]
    )
    checks["telemetry"] = telemetry
    if not telemetry["passed"]:
        errors.append("GPU温度またはrecovery telemetryを安全範囲で取得できません")

    port_available, port_error = check_port(args.host, args.port)
    checks["network"] = {
        "host": args.host,
        "port": args.port,
        "bind_available": port_available,
        "error": port_error,
    }
    if not port_available:
        errors.append(f"local port {args.port}を確保できません")

    payload = {
        "kind": "moe_upstream_preflight",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "errors_ja": errors,
        "result": "PASS" if not errors else "FAIL",
    }
    atomic_write_json(args.output, payload)
    if errors:
        for error in errors:
            print(f"停止: {error}", file=os.sys.stderr)
        return 2
    print("高負荷実行前check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
