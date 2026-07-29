#!/usr/bin/env python3
"""上流MoE一般応答baselineの結果を日本語reportとmanifestへ集約する。"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"read_error_ja": "JSONが途中で終了しています"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    samples: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            samples.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return samples


def numeric_values(samples: list[dict[str, Any]], key: str) -> list[float]:
    return [float(sample[key]) for sample in samples if sample.get(key) is not None]


def range_text(values: list[float], suffix: str = "") -> str:
    if not values:
        return "取得不可"
    return f"{min(values):.1f}–{max(values):.1f}{suffix}"


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def atomic_write_text(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--started-utc", required=True)
    parser.add_argument("--thermal-limit-c", type=int, required=True)
    parser.add_argument("--chat-status", type=int, default=99)
    parser.add_argument("--guard-status", type=int, default=99)
    parser.add_argument("--process-monitor-status", type=int, default=99)
    parser.add_argument("--server-status", type=int, default=99)
    parser.add_argument("--shutdown-requested", action="store_true")
    parser.add_argument("--server-forced-kill", action="store_true")
    args = parser.parse_args()

    run_dir = args.run_dir
    preflight = read_json(run_dir / "preflight.json")
    chat = read_json(run_dir / "chat" / "summary.json")
    gpu_samples = read_jsonl(run_dir / "telemetry-gpu.jsonl")
    process_samples = read_jsonl(run_dir / "telemetry-process.jsonl")

    temperatures = numeric_values(gpu_samples, "temperature_c")
    activities = numeric_values(gpu_samples, "gpu_activity_percent")
    powers = numeric_values(gpu_samples, "total_power_w")
    fans = numeric_values(gpu_samples, "fan_speed_rpm")
    recoveries = numeric_values(gpu_samples, "gpu_recovery_count")
    cpu_percentages = numeric_values(process_samples, "cpu_percent")
    rss_kib = numeric_values(process_samples, "rss_kib")
    load_one = [
        float(sample["load_average"][0])
        for sample in process_samples
        if isinstance(sample.get("load_average"), list) and sample["load_average"]
    ]

    thermal_abort = any(bool(sample.get("thermal_abort")) for sample in gpu_samples)
    telemetry_abort = any(bool(sample.get("telemetry_abort")) for sample in gpu_samples)
    sample_limit_abort = any(bool(sample.get("sample_limit_abort")) for sample in gpu_samples)
    telemetry_complete = bool(
        gpu_samples
        and temperatures
        and recoveries
        and all(sample.get("telemetry_available") for sample in gpu_samples)
    )
    recovery_delta = (max(recoveries) - min(recoveries)) if recoveries else None
    recovery_ok = recovery_delta == 0
    process_monitor_complete = bool(process_samples and cpu_percentages and rss_kib and load_one)
    server_shutdown_ok = (
        args.shutdown_requested
        and not args.server_forced_kill
        and args.server_status in (0, 143)
    )
    all_cases_passed = bool(chat.get("all_passed"))
    passed = (
        preflight.get("result") == "PASS"
        and args.chat_status == 0
        and all_cases_passed
        and args.guard_status == 0
        and args.process_monitor_status == 0
        and process_monitor_complete
        and not thermal_abort
        and not telemetry_abort
        and not sample_limit_abort
        and telemetry_complete
        and recovery_ok
        and server_shutdown_ok
    )

    case_results = chat.get("cases") if isinstance(chat.get("cases"), list) else []
    manifest = {
        "kind": "moe_upstream_chat_baseline",
        "started_utc": args.started_utc,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": args.git_commit,
        "scope": {
            "fam_connected": False,
            "head_connected": False,
            "router_override_applied": False,
        },
        "runtime": {
            "project": "llama.cpp",
            "release": "b9637",
            "commit": "aedb2a5e9",
            "architecture": "x86_64",
            "compute": "Accelerate CPU-only",
        },
        "verified_artifacts": preflight.get("checks", {}).get("artifacts"),
        "model": {
            "repository": "ibm-granite/granite-4.0-h-tiny-GGUF",
            "revision": "08d5a8a9741dd5c1a95d2d39e25253226aa1464e",
            "file": "granite-4.0-h-tiny-Q4_K_M.gguf",
            "quantization": "Q4_K_M",
        },
        "server_configuration": {
            "device": "none",
            "n_gpu_layers": 0,
            "kv_offload": False,
            "threads": 6,
            "threads_batch": 6,
            "context_size": 2048,
            "batch_size": 512,
            "ubatch_size": 128,
            "parallel": 1,
            "jinja": True,
            "prompt_cache": False,
        },
        "generation_configuration": {
            "temperature": 0.0,
            "seed": 424242,
            "max_tokens": 96,
            "top_k": 1,
            "top_p": 1.0,
            "min_p": 0.0,
        },
        "thermal_limit_c": args.thermal_limit_c,
        "statuses": {
            "chat": args.chat_status,
            "thermal_guard": args.guard_status,
            "process_monitor": args.process_monitor_status,
            "server_after_shutdown": args.server_status,
            "shutdown_requested_by_runner": args.shutdown_requested,
            "server_forced_kill": args.server_forced_kill,
        },
        "telemetry_summary": {
            "gpu_samples": len(gpu_samples),
            "process_samples": len(process_samples),
            "gpu_temperature_c": {"minimum": min(temperatures), "maximum": max(temperatures)} if temperatures else None,
            "gpu_activity_percent": {"minimum": min(activities), "maximum": max(activities)} if activities else None,
            "gpu_power_w": {"minimum": min(powers), "maximum": max(powers)} if powers else None,
            "gpu_recovery_delta": recovery_delta,
            "maximum_process_cpu_percent": max(cpu_percentages) if cpu_percentages else None,
            "maximum_process_rss_kib": max(rss_kib) if rss_kib else None,
            "maximum_load_average_1m": max(load_one) if load_one else None,
            "thermal_abort": thermal_abort,
            "telemetry_abort": telemetry_abort,
            "sample_limit_abort": sample_limit_abort,
            "telemetry_complete": telemetry_complete,
            "process_monitor_complete": process_monitor_complete,
            "cpu_temperature_c": None,
        },
        "case_results": case_results,
        "result": "PASS" if passed else "FAIL",
    }
    atomic_write_json(run_dir / "manifest.json", manifest)

    lines = [
        "# 上流MoE一般応答baseline実測レポート",
        "",
        f"- Git commit: `{args.git_commit}`",
        f"- 総合結果: **{'PASS' if passed else 'FAIL'}**",
        "- 対象: IBM Granite 4.0 H-Tiny Q4_K_M + llama.cpp b9637 x86_64",
        "- 演算経路: Accelerate CPU-only（Metal / GPU offloadなし）",
        "- FAM接続: なし",
        "- local HEAD接続: なし",
        "- router override: なし",
        f"- Thermal guard: {args.thermal_limit_c} °C",
        f"- Thermal abort: {'あり' if thermal_abort else 'なし'}",
        f"- Telemetry abort: {'あり' if telemetry_abort else 'なし'}",
        f"- Sample limit abort: {'あり' if sample_limit_abort else 'なし'}",
        f"- Telemetry完全性: {'PASS' if telemetry_complete else 'FAIL'}",
        f"- Process監視完全性: {'PASS' if process_monitor_complete else 'FAIL'}",
        f"- GPU温度: {range_text(temperatures, ' °C')}",
        f"- GPU activity: {range_text(activities, ' %')}",
        f"- GPU power: {range_text(powers, ' W')}",
        f"- GPU fan: {range_text(fans, ' RPM')}",
        f"- GPU recovery増分: {recovery_delta if recovery_delta is not None else '取得不可'}",
        f"- llama-server最大CPU使用率: {max(cpu_percentages):.1f} %" if cpu_percentages else "- llama-server最大CPU使用率: 取得不可",
        f"- llama-server最大RSS: {max(rss_kib) / 1024:.1f} MiB" if rss_kib else "- llama-server最大RSS: 取得不可",
        f"- 最大1分load average: {max(load_one):.2f}" if load_one else "- 最大1分load average: 取得不可",
        "- CPU温度: 非root CLIから取得できないため未記録",
        "",
        "## 会話case",
        "",
        "| case | 目的 | HTTP | 秒 | 判定 | 内容 |",
        "|---|---|---:|---:|---|---|",
    ]
    for case in case_results:
        lines.append(
            "| {id} | {description} | {status} | {elapsed:.2f} | {passed} | {message} |".format(
                id=markdown_cell(case.get("id", "不明")),
                description=markdown_cell(case.get("description_ja", "")),
                status=markdown_cell(case.get("status_code", "-")),
                elapsed=float(case.get("elapsed_seconds", 0.0)),
                passed="PASS" if case.get("passed") else "FAIL",
                message=markdown_cell(case.get("assertion_message_ja", "")),
            )
        )
    if not case_results:
        lines.append("| - | 応答caseを完走できず | - | 0.00 | FAIL | chat summaryを確認 |")

    preflight_errors = preflight.get("errors_ja") if isinstance(preflight.get("errors_ja"), list) else []
    lines.extend(
        [
            "",
            "## 実行status",
            "",
            f"- preflight: {preflight.get('result', '取得不可')}",
            f"- chat runner exit: {args.chat_status}",
            f"- thermal guard exit: {args.guard_status}",
            f"- process monitor exit: {args.process_monitor_status}",
            f"- server shutdown後status: {args.server_status}（runnerのSIGTERM終了は異常扱いしない）",
            f"- runnerからのshutdown要求: {'あり' if args.shutdown_requested else 'なし'}",
            f"- server強制KILL: {'あり' if args.server_forced_kill else 'なし'}",
        ]
    )
    if preflight_errors:
        lines.extend(["", "### preflight停止理由", ""])
        lines.extend(f"- {error}" for error in preflight_errors)
    lines.extend(
        [
            "",
            "## 判定と次工程",
            "",
            "- このrunは上流runtime/modelだけの環境baselineであり、FAM algorithmとlocal HEADを一切実行していない。",
            "- PASS時のみ、別commitでFAM未接続HEAD bypassのbuildへ進む。",
            "- HEAD bypassがPASSしてもFAM encode、優先順位規則、router replay注入には着手せず停止する。",
            "",
        ]
    )
    atomic_write_text(run_dir / "REPORT.md", "\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
