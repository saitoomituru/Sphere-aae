#!/usr/bin/env python3
"""FAM未接続MoE HEAD bypass baselineを日本語reportへfail-closedで集約する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value) is not None


def is_zero_status(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def read_json(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata: dict[str, Any] = {
        "exists": path.is_file(),
        "valid_json_object": False,
        "read_error": False,
    }
    if not path.is_file():
        return {}, metadata
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        metadata["read_error"] = True
        return {}, metadata
    if not isinstance(value, dict):
        return {}, metadata
    metadata["valid_json_object"] = True
    return value, metadata


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {
        "exists": path.is_file(),
        "line_count": 0,
        "blank_line_count": 0,
        "invalid_line_count": 0,
        "read_error": False,
    }
    if not path.is_file():
        return samples, metadata
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                metadata["line_count"] += 1
                if not line.strip():
                    metadata["blank_line_count"] += 1
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    metadata["invalid_line_count"] += 1
                    continue
                if not isinstance(value, dict):
                    metadata["invalid_line_count"] += 1
                    continue
                samples.append(value)
    except (OSError, UnicodeError):
        metadata["read_error"] = True
    metadata["valid_sample_count"] = len(samples)
    return samples, metadata


def atomic_write(path: Path, content: bytes) -> None:
    """同一directory内で置換し、fileとdirectory双方をfsyncする。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}"
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write(path, content)


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write(path, content.encode("utf-8"))


def find_repo_root(run_dir: Path) -> Path | None:
    resolved = run_dir.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def display_path(path: Path, repo_root: Path | None) -> str:
    """report/manifestへ絶対pathを出さず、可能ならrepository相対pathにする。"""
    resolved = path.resolve(strict=False)
    if repo_root is not None:
        try:
            return resolved.relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            pass
    return f"<REPO外>/{resolved.name or 'artifact'}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> tuple[str, int, int]:
    """relative pathとfile内容を含む決定的directory tree hashを作る。"""
    digest = hashlib.sha256()
    files = sorted(child for child in path.rglob("*") if child.is_file())
    total_size = 0
    for child in files:
        relative = child.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with child.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                total_size += len(chunk)
        digest.update(b"\0")
    return digest.hexdigest(), len(files), total_size


def compiled_model_record(path: Path, repo_root: Path | None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": display_path(path, repo_root),
        "exists": path.exists(),
        "is_directory": path.is_dir(),
        "hash_complete": False,
    }
    if not path.is_dir():
        return record
    try:
        tree_hash, file_count, total_size = sha256_tree(path)
    except OSError:
        record["hash_error"] = True
        return record
    record.update(
        {
            "sha256_tree": tree_hash,
            "file_count": file_count,
            "size_bytes": total_size,
            "hash_complete": file_count > 0 and is_sha256(tree_hash),
        }
    )
    return record


def binary_record(path: Path, repo_root: Path | None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": display_path(path, repo_root),
        "exists": path.is_file(),
        "is_executable": path.is_file() and os.access(path, os.X_OK),
        "hash_complete": False,
    }
    if not path.is_file():
        return record
    try:
        digest = sha256_file(path)
        size = path.stat().st_size
    except OSError:
        record["hash_error"] = True
        return record
    record.update(
        {
            "sha256": digest,
            "size_bytes": size,
            "hash_complete": size > 0 and is_sha256(digest),
        }
    )
    return record


def number_range(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    return {"minimum": min(values), "maximum": max(values)}


def gpu_file_summary(path: Path, run_dir: Path, thermal_limit_c: float) -> dict[str, Any]:
    samples, source = read_jsonl(path)
    temperatures = [
        float(sample["temperature_c"])
        for sample in samples
        if is_finite_number(sample.get("temperature_c"))
    ]
    recoveries = [
        float(sample["gpu_recovery_count"])
        for sample in samples
        if is_finite_number(sample.get("gpu_recovery_count"))
    ]
    complete_sample_count = 0
    for sample in samples:
        load_average = sample.get("load_average")
        complete = (
            isinstance(sample.get("timestamp_utc"), str)
            and bool(sample.get("timestamp_utc"))
            and isinstance(sample.get("sample_index"), int)
            and not isinstance(sample.get("sample_index"), bool)
            and sample.get("ioreg_returncode") == 0
            and sample.get("telemetry_available") is True
            and is_finite_number(sample.get("temperature_c"))
            and float(sample["temperature_c"]) < thermal_limit_c
            and is_finite_number(sample.get("gpu_recovery_count"))
            and sample.get("thermal_abort") is False
            and sample.get("telemetry_abort") is False
            and sample.get("sample_limit_abort") is False
            and isinstance(load_average, list)
            and len(load_average) >= 1
            and all(is_finite_number(value) for value in load_average)
        )
        if complete:
            complete_sample_count += 1

    recovery_delta = max(recoveries) - min(recoveries) if recoveries else None
    thermal_abort = any(sample.get("thermal_abort") is True for sample in samples)
    telemetry_abort = any(sample.get("telemetry_abort") is True for sample in samples)
    sample_limit_abort = any(sample.get("sample_limit_abort") is True for sample in samples)
    samples_complete = bool(samples) and complete_sample_count == len(samples)
    source_complete = (
        source["exists"]
        and not source["read_error"]
        and source["blank_line_count"] == 0
        and source["invalid_line_count"] == 0
    )
    passed = bool(
        source_complete
        and samples_complete
        and temperatures
        and max(temperatures) < thermal_limit_c
        and recoveries
        and recovery_delta == 0
        and not thermal_abort
        and not telemetry_abort
        and not sample_limit_abort
    )
    try:
        relative = path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        relative = path.name
    return {
        "path": relative,
        **source,
        "complete_sample_count": complete_sample_count,
        "all_samples_complete": samples_complete,
        "temperature_c": number_range(temperatures),
        "recovery_count": number_range(recoveries),
        "recovery_delta": recovery_delta,
        "thermal_abort": thermal_abort,
        "telemetry_abort": telemetry_abort,
        "sample_limit_abort": sample_limit_abort,
        "below_thermal_limit": bool(temperatures and max(temperatures) < thermal_limit_c),
        "passed": passed,
    }


def process_summary(path: Path, run_dir: Path) -> dict[str, Any]:
    samples, source = read_jsonl(path)
    complete_sample_count = 0
    cpu_values: list[float] = []
    rss_values: list[float] = []
    vsz_values: list[float] = []
    load_values: list[float] = []
    pids: list[int] = []
    indices: list[int] = []
    for sample in samples:
        load_average = sample.get("load_average")
        state = sample.get("state")
        complete = (
            isinstance(sample.get("timestamp_utc"), str)
            and bool(sample.get("timestamp_utc"))
            and isinstance(sample.get("sample_index"), int)
            and not isinstance(sample.get("sample_index"), bool)
            and isinstance(sample.get("pid"), int)
            and not isinstance(sample.get("pid"), bool)
            and sample["pid"] > 0
            and is_finite_number(sample.get("cpu_percent"))
            and float(sample["cpu_percent"]) >= 0
            and is_finite_number(sample.get("rss_kib"))
            and float(sample["rss_kib"]) >= 0
            and is_finite_number(sample.get("vsz_kib"))
            and float(sample["vsz_kib"]) >= 0
            and isinstance(sample.get("elapsed"), str)
            and bool(sample.get("elapsed"))
            and isinstance(state, str)
            and bool(state)
            and not state.startswith("Z")
            and isinstance(load_average, list)
            and len(load_average) >= 1
            and all(is_finite_number(value) and float(value) >= 0 for value in load_average)
        )
        if complete:
            complete_sample_count += 1
            cpu_values.append(float(sample["cpu_percent"]))
            rss_values.append(float(sample["rss_kib"]))
            vsz_values.append(float(sample["vsz_kib"]))
            load_values.append(float(load_average[0]))
            pids.append(int(sample["pid"]))
            indices.append(int(sample["sample_index"]))

    sequence_complete = indices == list(range(len(indices)))
    one_process = bool(pids) and len(set(pids)) == 1
    samples_complete = bool(samples) and complete_sample_count == len(samples)
    source_complete = (
        source["exists"]
        and not source["read_error"]
        and source["blank_line_count"] == 0
        and source["invalid_line_count"] == 0
    )
    passed = bool(source_complete and samples_complete and sequence_complete and one_process)
    try:
        relative = path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        relative = path.name
    return {
        "path": relative,
        **source,
        "complete_sample_count": complete_sample_count,
        "all_samples_complete": samples_complete,
        "sample_index_sequence_complete": sequence_complete,
        "single_process": one_process,
        "maximum_cpu_percent": max(cpu_values) if cpu_values else None,
        "maximum_rss_kib": max(rss_values) if rss_values else None,
        "maximum_vsz_kib": max(vsz_values) if vsz_values else None,
        "maximum_load_average_1m": max(load_values) if load_values else None,
        "passed": passed,
    }


def fixture_assessment(fixture: dict[str, Any], source: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    checks = {
        "document_valid": source["valid_json_object"],
        "input_mode_zero": fixture.get("input_mode") == "zero",
        "fam_disabled": "fam_enabled" in fixture and fixture.get("fam_enabled") is False,
        "head_observe_only": fixture.get("head_mode") == "observe_only",
        "router_override_disabled": (
            "router_override_applied" in fixture
            and fixture.get("router_override_applied") is False
        ),
        "model_sha256_recorded": is_sha256(fixture.get("model_sha256")),
        "fixture_sha256_recorded": is_sha256(fixture.get("fixture_sha256")),
        "weights_sha256_recorded": is_sha256(fixture.get("weights_sha256")),
    }
    summary = {
        "model_name": fixture.get("model_name"),
        "coremltools_version": fixture.get("coremltools_version"),
        "numpy_version": fixture.get("numpy_version"),
        "batch_size": fixture.get("batch_size"),
        "input_mode": fixture.get("input_mode"),
        "fam_enabled": fixture.get("fam_enabled"),
        "head_mode": fixture.get("head_mode"),
        "router_override_applied": fixture.get("router_override_applied"),
        "source_model_sha256_tree": fixture.get("model_sha256"),
        "fixture_sha256": fixture.get("fixture_sha256"),
        "weights_sha256": fixture.get("weights_sha256"),
        "checks": checks,
    }
    return summary, all(checks.values())


def finite_number_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(is_finite_number(item) for item in value)


def integer_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    )


def head_assessment(head: dict[str, Any], source: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    actual_logits = head.get("actual_logits")
    expected_logits = head.get("expected_logits")
    actual_shape = head.get("actual_output_shape")
    expected_shape = head.get("expected_output_shape")
    actual_top_k = head.get("actual_top_k")
    expected_top_k = head.get("expected_top_k")
    repeat_error = head.get("repeat_max_abs_error")
    reference_error = head.get("max_abs_error")
    checks = {
        "document_valid": source["valid_json_object"],
        "head_passed": head.get("passed") is True,
        "head_observe_only": head.get("head_mode") == "observe_only",
        "fam_disabled": "fam_enabled" in head and head.get("fam_enabled") is False,
        "input_mode_zero": head.get("input_mode") == "zero",
        "input_all_zero": head.get("input_all_zero") is True,
        "cpu_only": head.get("compute_units") == "cpuOnly",
        "router_override_disabled": (
            "router_override_applied" in head and head.get("router_override_applied") is False
        ),
        "logits_finite_flag": head.get("logits_finite") is True,
        "actual_logits_finite": finite_number_list(actual_logits),
        "expected_logits_finite": finite_number_list(expected_logits),
        "shape_match_flag": head.get("output_shape_matches") is True,
        "shape_values_match": (
            integer_list(actual_shape)
            and integer_list(expected_shape)
            and actual_shape == expected_shape
        ),
        "top_k_match_flag": head.get("top_k_match") is True,
        "top_k_values_match": (
            integer_list(actual_top_k)
            and integer_list(expected_top_k)
            and actual_top_k == expected_top_k
        ),
        "repeat_match_flag": head.get("deterministic_repeat_match") is True,
        "repeat_error_within_tolerance": (
            is_finite_number(repeat_error) and float(repeat_error) <= 1e-7
        ),
        "reference_error_within_tolerance": (
            is_finite_number(reference_error) and float(reference_error) <= 1e-5
        ),
        "inference_repeated": (
            isinstance(head.get("inference_count"), int)
            and not isinstance(head.get("inference_count"), bool)
            and head["inference_count"] >= 2
        ),
    }
    summary = {
        "model_name": head.get("model_name"),
        "head_mode": head.get("head_mode"),
        "fam_enabled": head.get("fam_enabled"),
        "input_mode": head.get("input_mode"),
        "input_all_zero": head.get("input_all_zero"),
        "compute_units": head.get("compute_units"),
        "router_override_applied": head.get("router_override_applied"),
        "inference_count": head.get("inference_count"),
        "latency_ms": head.get("latency_ms"),
        "actual_output_shape": actual_shape,
        "expected_output_shape": expected_shape,
        "output_shape_matches": head.get("output_shape_matches"),
        "logits_finite": head.get("logits_finite"),
        "actual_logits": actual_logits,
        "expected_logits": expected_logits,
        "actual_top_k": actual_top_k,
        "expected_top_k": expected_top_k,
        "top_k_match": head.get("top_k_match"),
        "deterministic_repeat_match": head.get("deterministic_repeat_match"),
        "repeat_max_abs_error": repeat_error,
        "max_abs_error": reference_error,
        "passed": head.get("passed"),
        "checks": checks,
    }
    return summary, all(checks.values())


def comparison_assessment(
    comparison: dict[str, Any], source: dict[str, Any], head: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    responses = comparison.get("responses")
    if not isinstance(responses, dict):
        responses = {}
    hashes: dict[str, object] = {}
    response_summaries: dict[str, dict[str, object]] = {}
    for label in ("a1", "a2", "b"):
        response = responses.get(label)
        hashes[label] = (
            response.get("canonical_message_sha256") if isinstance(response, dict) else None
        )
        response_summaries[label] = {
            "status_code": response.get("status_code") if isinstance(response, dict) else None,
            "elapsed_seconds": (
                response.get("elapsed_seconds") if isinstance(response, dict) else None
            ),
            "passed": response.get("passed") if isinstance(response, dict) else None,
            "assertion_message_ja": (
                response.get("assertion_message_ja") if isinstance(response, dict) else None
            ),
            "canonical_message_sha256": hashes[label],
        }
    hash_values = list(hashes.values())
    hashes_complete = all(is_sha256(value) for value in hash_values)
    hashes_equal = hashes_complete and len(set(hash_values)) == 1

    comparison_head = comparison.get("head")
    if not isinstance(comparison_head, dict):
        comparison_head = {}
    head_consistent = (
        comparison_head.get("passed") is True
        and comparison_head.get("timed_out") is False
        and comparison_head.get("result_available") is True
        and comparison_head.get("result_passed") is True
        and comparison_head.get("fam_disabled") is True
        and comparison_head.get("input_zero") is True
        and comparison_head.get("override_disabled") is True
        and comparison_head.get("observe_only") is True
        and comparison_head.get("result_passed") == (head.get("passed") is True)
        and comparison_head.get("fam_disabled") == (head.get("fam_enabled") is False)
        and comparison_head.get("input_zero")
        == (head.get("input_mode") == "zero" and head.get("input_all_zero") is True)
        and comparison_head.get("override_disabled")
        == (head.get("router_override_applied") is False)
        and comparison_head.get("observe_only") == (head.get("head_mode") == "observe_only")
    )
    head_exit_code = comparison_head.get("exit_code")
    response_records_complete = all(
        isinstance(responses.get(label), dict)
        and responses[label].get("status_code") == 200
        and responses[label].get("passed") is True
        for label in ("a1", "a2", "b")
    )
    health_checks = comparison.get("health_checks")
    if not isinstance(health_checks, list):
        health_checks = []
    health_checks_complete = bool(health_checks) and all(
        isinstance(item, dict) and item.get("passed") is True for item in health_checks
    )
    initial_health = comparison.get("initial_health")
    initial_health_ready = bool(
        isinstance(initial_health, dict)
        and initial_health.get("ready") is True
        and initial_health.get("status_code") == 200
        and isinstance(initial_health.get("health"), dict)
        and initial_health["health"].get("status") == "ok"
    )
    checks = {
        "document_valid": source["valid_json_object"],
        "response_records_complete": response_records_complete,
        "initial_health_ready": initial_health_ready,
        "health_checks_complete": health_checks_complete,
        "server_alive_final": comparison.get("server_alive_final") is True,
        "a1_a2_match": comparison.get("a1_a2_match") is True,
        "a1_b_match": comparison.get("a1_b_match") is True,
        "a2_b_match": comparison.get("a2_b_match") is True,
        "all_responses_match": comparison.get("all_responses_match") is True,
        "canonical_hashes_complete": hashes_complete,
        "canonical_hashes_equal": hashes_equal,
        "head_exit_zero": is_zero_status(head_exit_code),
        "head_summary_consistent": head_consistent,
        "all_passed": comparison.get("all_passed") is True,
    }
    summary = {
        "a1_a2_match": comparison.get("a1_a2_match"),
        "a1_b_match": comparison.get("a1_b_match"),
        "a2_b_match": comparison.get("a2_b_match"),
        "all_responses_match": comparison.get("all_responses_match"),
        "responses": response_summaries,
        "canonical_message_sha256": hashes,
        "health_check_count": len(health_checks),
        "initial_health_ready": initial_health_ready,
        "all_health_checks_passed": health_checks_complete,
        "server_alive_final": comparison.get("server_alive_final"),
        "head": {
            "exit_code": head_exit_code,
            "timed_out": comparison_head.get("timed_out"),
            "result_available": comparison_head.get("result_available"),
            "result_passed": comparison_head.get("result_passed"),
            "fam_disabled": comparison_head.get("fam_disabled"),
            "input_zero": comparison_head.get("input_zero"),
            "override_disabled": comparison_head.get("override_disabled"),
            "observe_only": comparison_head.get("observe_only"),
            "passed": comparison_head.get("passed"),
        },
        "all_passed": comparison.get("all_passed"),
        "checks": checks,
    }
    return summary, all(checks.values())


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def pass_text(value: bool) -> str:
    return "PASS" if value else "FAIL"


def range_text(value: object, suffix: str = "") -> str:
    if not isinstance(value, dict):
        return "取得不可"
    minimum = value.get("minimum")
    maximum = value.get("maximum")
    if not is_finite_number(minimum) or not is_finite_number(maximum):
        return "取得不可"
    return f"{float(minimum):.1f}–{float(maximum):.1f}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--started-utc", required=True)
    parser.add_argument("--thermal-limit-c", type=float, required=True)
    parser.add_argument("--fixture-build-status", type=int, default=99)
    parser.add_argument("--fixture-guard-status", type=int, default=99)
    parser.add_argument("--compiler-status", type=int, default=99)
    parser.add_argument("--compiler-guard-status", type=int, default=99)
    parser.add_argument("--swift-build-status", type=int, default=99)
    parser.add_argument("--swift-guard-status", type=int, default=99)
    parser.add_argument("--comparison-status", type=int, default=99)
    parser.add_argument("--server-guard-status", type=int, default=99)
    parser.add_argument("--process-monitor-status", type=int, default=99)
    parser.add_argument("--server-status", type=int, default=99)
    parser.add_argument("--shutdown-requested", action="store_true")
    parser.add_argument("--server-forced-kill", action="store_true")
    parser.add_argument("--compiled-model", type=Path, required=True)
    parser.add_argument("--head-binary", type=Path, required=True)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    repo_root = find_repo_root(run_dir)
    compiled_model_path = args.compiled_model.resolve(strict=False)
    head_binary_path = args.head_binary.resolve(strict=False)

    preflight, preflight_source = read_json(run_dir / "preflight.json")
    fixture, fixture_source = read_json(run_dir / "head" / "fixture-manifest.json")
    comparison, comparison_source = read_json(run_dir / "comparison" / "summary.json")
    head, head_source = read_json(run_dir / "comparison" / "head-result.json")

    fixture_summary, fixture_passed = fixture_assessment(fixture, fixture_source)
    head_summary, head_passed = head_assessment(head, head_source)
    comparison_summary, comparison_passed = comparison_assessment(
        comparison, comparison_source, head
    )

    preflight_checks = preflight.get("checks")
    if not isinstance(preflight_checks, dict):
        preflight_checks = {}
    preflight_git = preflight_checks.get("git", {})
    if not isinstance(preflight_git, dict):
        preflight_git = {}
    git_commit_valid = GIT_COMMIT_PATTERN.fullmatch(args.git_commit) is not None
    git_saved_remotely = (
        git_commit_valid
        and preflight_git.get("working_tree_clean") is True
        and preflight_git.get("live_remote_checked") is True
        and preflight_git.get("head") == args.git_commit
        and preflight_git.get("cached_upstream_head") == args.git_commit
        and preflight_git.get("live_remote_head") == args.git_commit
    )
    preflight_passed = bool(
        preflight_source["valid_json_object"]
        and preflight.get("result") == "PASS"
        and git_saved_remotely
    )

    compiled_model = compiled_model_record(compiled_model_path, repo_root)
    head_binary = binary_record(head_binary_path, repo_root)
    artifacts_passed = bool(
        compiled_model.get("is_directory")
        and compiled_model.get("hash_complete")
        and head_binary.get("exists")
        and head_binary.get("is_executable")
        and head_binary.get("hash_complete")
    )

    gpu_paths = sorted(run_dir.glob("telemetry-gpu-*.jsonl"))
    gpu_files = [gpu_file_summary(path, run_dir, args.thermal_limit_c) for path in gpu_paths]
    gpu_recovery_ranges = [
        record["recovery_count"]
        for record in gpu_files
        if isinstance(record.get("recovery_count"), dict)
    ]
    all_recovery_values = [
        float(value)
        for record in gpu_recovery_ranges
        for value in (record.get("minimum"), record.get("maximum"))
        if is_finite_number(value)
    ]
    global_recovery_delta = (
        max(all_recovery_values) - min(all_recovery_values)
        if all_recovery_values
        else None
    )
    gpu_telemetry_passed = bool(
        len(gpu_files) >= 4
        and all(record.get("passed") is True for record in gpu_files)
        and global_recovery_delta == 0
    )
    gpu_summary = {
        "expected_minimum_file_count": 4,
        "file_count": len(gpu_files),
        "sample_count": sum(int(record.get("valid_sample_count", 0)) for record in gpu_files),
        "global_recovery_delta": global_recovery_delta,
        "all_files_passed": gpu_telemetry_passed,
        "files": gpu_files,
    }

    server_process = process_summary(run_dir / "telemetry-process-server.jsonl", run_dir)
    process_telemetry_passed = bool(
        is_zero_status(args.process_monitor_status) and server_process.get("passed") is True
    )

    status_values = {
        "fixture_build": args.fixture_build_status,
        "fixture_guard": args.fixture_guard_status,
        "coremlcompiler": args.compiler_status,
        "coremlcompiler_guard": args.compiler_guard_status,
        "swift_build": args.swift_build_status,
        "swift_build_guard": args.swift_guard_status,
        "comparison": args.comparison_status,
        "server_guard": args.server_guard_status,
        "process_monitor": args.process_monitor_status,
        "server_after_shutdown": args.server_status,
    }
    required_zero_statuses = (
        "fixture_build",
        "fixture_guard",
        "coremlcompiler",
        "coremlcompiler_guard",
        "swift_build",
        "swift_build_guard",
        "comparison",
        "server_guard",
        "process_monitor",
    )
    execution_statuses_passed = all(
        is_zero_status(status_values[name]) for name in required_zero_statuses
    )
    shutdown_passed = bool(
        args.shutdown_requested
        and not args.server_forced_kill
        and args.server_status in (0, 143)
    )

    checks = {
        "preflight_and_remote_save": preflight_passed,
        "all_build_guard_comparison_statuses_zero": execution_statuses_passed,
        "compiled_model_and_head_binary_hashed": artifacts_passed,
        "fixture_manifest_fam_free": fixture_passed,
        "head_zero_input_observe_only": head_passed,
        "a1_a2_b_identical": comparison_passed,
        "all_gpu_telemetry_complete": gpu_telemetry_passed,
        "server_process_telemetry_complete": process_telemetry_passed,
        "server_sigterm_shutdown_without_kill": shutdown_passed,
    }
    failures_ja_by_check = {
        "preflight_and_remote_save": "preflightまたはremote保存状態を確認できません",
        "all_build_guard_comparison_statuses_zero": "build・guard・比較のいずれかがexit 0ではありません",
        "compiled_model_and_head_binary_hashed": "compiled model treeまたはHEAD binaryのSHA256を完全に取得できません",
        "fixture_manifest_fam_free": "fixture manifestのFAM未接続条件またはhash記録が不完全です",
        "head_zero_input_observe_only": "HEAD結果がzero input・observe-only・finite/shape/top-k/repeat条件を満たしません",
        "a1_a2_b_identical": "A1・A2・Bのcanonical応答一致または比較HEAD情報を確認できません",
        "all_gpu_telemetry_complete": "GPU telemetryが4系統未満、不完全、温度超過、recovery増加、またはabortを含みます",
        "server_process_telemetry_complete": "llama-server process telemetryが不完全です",
        "server_sigterm_shutdown_without_kill": "runnerのSIGTERMによる通常停止、またはSIGKILL不使用を確認できません",
    }
    failures_ja = [
        failures_ja_by_check[name] for name, passed in checks.items() if not passed
    ]
    passed = all(checks.values())

    manifest = {
        "kind": "moe_head_bypass_baseline",
        "started_utc": args.started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": args.git_commit if git_commit_valid else "<INVALID_GIT_COMMIT>",
        "scope": {
            "fam_connected": False,
            "head_mode": "observe_only",
            "input_mode": "zero",
            "router_override_applied": False,
            "moe_response_mutation_allowed": False,
        },
        "input_documents": {
            "preflight": {"path": "preflight.json", **preflight_source},
            "fixture_manifest": {
                "path": "head/fixture-manifest.json",
                **fixture_source,
            },
            "comparison_summary": {
                "path": "comparison/summary.json",
                **comparison_source,
            },
            "head_result": {
                "path": "comparison/head-result.json",
                **head_source,
            },
        },
        "preflight": {
            "result": preflight.get("result"),
            "git_saved_remotely": git_saved_remotely,
        },
        "statuses": status_values,
        "shutdown": {
            "requested_by_runner": args.shutdown_requested,
            "server_forced_kill": args.server_forced_kill,
            "normal_sigterm_exit": shutdown_passed,
        },
        "artifacts": {
            "compiled_model": compiled_model,
            "head_binary": head_binary,
        },
        "fixture": fixture_summary,
        "head_result": head_summary,
        "comparison": comparison_summary,
        "thermal_limit_c": args.thermal_limit_c,
        "gpu_telemetry": gpu_summary,
        "server_process_telemetry": server_process,
        "checks": checks,
        "failures_ja": failures_ja,
        "result": "PASS" if passed else "FAIL",
    }
    atomic_write_json(run_dir / "manifest.json", manifest)

    stage_rows = [
        ("fixture生成", args.fixture_build_status, is_zero_status(args.fixture_build_status)),
        ("fixture thermal guard", args.fixture_guard_status, is_zero_status(args.fixture_guard_status)),
        ("coremlcompiler", args.compiler_status, is_zero_status(args.compiler_status)),
        ("compiler thermal guard", args.compiler_guard_status, is_zero_status(args.compiler_guard_status)),
        ("Swift HEAD build", args.swift_build_status, is_zero_status(args.swift_build_status)),
        ("Swift build thermal guard", args.swift_guard_status, is_zero_status(args.swift_guard_status)),
        ("A/B比較", args.comparison_status, is_zero_status(args.comparison_status)),
        ("server thermal guard", args.server_guard_status, is_zero_status(args.server_guard_status)),
        ("server process監視", args.process_monitor_status, is_zero_status(args.process_monitor_status)),
        ("server停止後", args.server_status, args.server_status in (0, 143)),
    ]
    lines = [
        "# MoE HEAD bypass baseline実測レポート",
        "",
        f"- Git commit: `{args.git_commit if git_commit_valid else '<INVALID_GIT_COMMIT>'}`",
        f"- 総合結果: **{pass_text(passed)}**",
        "- 対象: 上流MoE一般応答 + local Core ML HEAD（FAM未接続）",
        "- HEAD mode: `observe_only`",
        "- HEAD input: `zero`",
        "- router override: なし",
        "- MoE応答へのHEAD出力注入: なし",
        f"- Thermal guard: {args.thermal_limit_c:g} °C",
        "",
        "## 工程status",
        "",
        "| 工程 | exit status | 判定 |",
        "|---|---:|---|",
    ]
    for label, status, row_passed in stage_rows:
        lines.append(
            f"| {markdown_cell(label)} | {status} | {pass_text(row_passed)} |"
        )

    lines.extend(
        [
            "",
            "## HEAD安全条件",
            "",
            "| 条件 | 値 | 判定 |",
            "|---|---|---|",
            f"| FAM無効 | `{head_summary.get('fam_enabled')}` | {pass_text(head_summary['checks']['fam_disabled'])} |",
            f"| zero input | `{head_summary.get('input_mode')}` / all-zero=`{head_summary.get('input_all_zero')}` | {pass_text(head_summary['checks']['input_mode_zero'] and head_summary['checks']['input_all_zero'])} |",
            f"| observe-only | `{head_summary.get('head_mode')}` | {pass_text(head_summary['checks']['head_observe_only'])} |",
            f"| router override無効 | `{head_summary.get('router_override_applied')}` | {pass_text(head_summary['checks']['router_override_disabled'])} |",
            f"| finite logits | max abs error=`{head_summary.get('max_abs_error')}` | {pass_text(head_summary['checks']['logits_finite_flag'] and head_summary['checks']['actual_logits_finite'])} |",
            f"| output shape一致 | `{head_summary.get('actual_output_shape')}` | {pass_text(head_summary['checks']['shape_match_flag'] and head_summary['checks']['shape_values_match'])} |",
            f"| stable top-k一致 | `{head_summary.get('actual_top_k')}` | {pass_text(head_summary['checks']['top_k_match_flag'] and head_summary['checks']['top_k_values_match'])} |",
            f"| repeat一致 | max abs error=`{head_summary.get('repeat_max_abs_error')}` | {pass_text(head_summary['checks']['repeat_match_flag'] and head_summary['checks']['repeat_error_within_tolerance'])} |",
            "",
            "## A1 / A2 / HEAD / B比較",
            "",
            f"- A1=A2: {pass_text(comparison_summary['checks']['a1_a2_match'])}",
            f"- A1=B: {pass_text(comparison_summary['checks']['a1_b_match'])}",
            f"- A2=B: {pass_text(comparison_summary['checks']['a2_b_match'])}",
            f"- canonical message SHA256一致: {pass_text(comparison_summary['checks']['canonical_hashes_equal'])}",
            f"- HEAD subprocess exit: `{comparison_summary['head'].get('exit_code')}`",
            "",
            "| 応答 | canonical message SHA256 |",
            "|---|---|",
        ]
    )
    for label in ("a1", "a2", "b"):
        digest = comparison_summary["canonical_message_sha256"].get(label)
        lines.append(f"| {label.upper()} | `{markdown_cell(digest)}` |")

    lines.extend(
        [
            "",
            "## 成果物identity",
            "",
            f"- compiled model: `{markdown_cell(compiled_model.get('path'))}`",
            f"- compiled model tree SHA256: `{markdown_cell(compiled_model.get('sha256_tree', '取得不可'))}`",
            f"- compiled model files: {compiled_model.get('file_count', 0)}",
            f"- HEAD binary: `{markdown_cell(head_binary.get('path'))}`",
            f"- HEAD binary SHA256: `{markdown_cell(head_binary.get('sha256', '取得不可'))}`",
            "",
            "## GPU telemetry",
            "",
            f"- 記録file数: {gpu_summary['file_count']}（最低4系統）",
            f"- 有効sample数: {gpu_summary['sample_count']}",
            f"- 全区間recovery増分: {gpu_summary['global_recovery_delta'] if gpu_summary['global_recovery_delta'] is not None else '取得不可'}",
            "- CPU温度: 非root CLIから取得できないため未記録",
            "",
            "| file | samples | GPU温度 | recovery増分 | abort | 判定 |",
            "|---|---:|---|---:|---|---|",
        ]
    )
    for record in gpu_files:
        abort_text = (
            "あり"
            if record["thermal_abort"]
            or record["telemetry_abort"]
            or record["sample_limit_abort"]
            else "なし"
        )
        recovery_delta_text = (
            record["recovery_delta"]
            if record["recovery_delta"] is not None
            else "取得不可"
        )
        lines.append(
            "| {path} | {samples} | {temperature} | {recovery} | {abort} | {passed} |".format(
                path=markdown_cell(record["path"]),
                samples=record["valid_sample_count"],
                temperature=range_text(record["temperature_c"], " °C"),
                recovery=recovery_delta_text,
                abort=abort_text,
                passed=pass_text(record["passed"]),
            )
        )
    if not gpu_files:
        lines.append("| - | 0 | 取得不可 | 取得不可 | 取得不可 | FAIL |")

    max_rss = server_process.get("maximum_rss_kib")
    max_rss_text = f"{float(max_rss) / 1024:.1f} MiB" if is_finite_number(max_rss) else "取得不可"
    max_cpu = server_process.get("maximum_cpu_percent")
    max_cpu_text = f"{float(max_cpu):.1f} %" if is_finite_number(max_cpu) else "取得不可"
    lines.extend(
        [
            "",
            "## llama-server監視と停止",
            "",
            f"- process samples: {server_process.get('valid_sample_count', 0)}",
            f"- 最大CPU使用率: {max_cpu_text}",
            f"- 最大RSS: {max_rss_text}",
            f"- process telemetry: {pass_text(process_telemetry_passed)}",
            f"- runnerからのSIGTERM要求: {'あり' if args.shutdown_requested else 'なし'}",
            f"- server強制SIGKILL: {'あり' if args.server_forced_kill else 'なし'}",
            f"- 通常停止判定: {pass_text(shutdown_passed)}",
            "",
            "## 判定",
            "",
        ]
    )
    if failures_ja:
        lines.extend(f"- FAIL: {message}" for message in failures_ja)
    else:
        lines.append("- 全必須条件を満たしたためPASS。")
    lines.extend(
        [
            "",
            "## 停止点",
            "",
            "- このrunではFAM encode、FAM優先順位規則、router replay注入を実装・実行していない。",
            "- HEADはzero inputの出力を観測しただけで、上流MoE応答へ一切反映していない。",
            "- PASS/FAILを問わず本工程で停止し、FAM algorithm調整は別承認後に行う。",
            "",
        ]
    )
    atomic_write_text(run_dir / "REPORT.md", "\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
