#!/usr/bin/env python3
"""Summarize Core ML smoke JSON and AMD telemetry as a Markdown report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def values(samples: list[dict[str, Any]], key: str) -> list[float]:
    return [float(sample[key]) for sample in samples if sample.get(key) is not None]


def range_text(data: list[float], suffix: str = "") -> str:
    return "取得不可" if not data else f"{min(data):.0f}–{max(data):.0f}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--thermal-limit-c", type=int, required=True)
    args = parser.parse_args()

    reports = [read_json(path) for path in sorted(args.run_dir.glob("result-*.json"))]
    telemetry_paths = sorted(args.run_dir.glob("telemetry-*.jsonl"))
    samples = [sample for path in telemetry_paths for sample in read_jsonl(path)]
    temperatures = values(samples, "temperature_c")
    activities = values(samples, "gpu_activity_percent")
    powers = values(samples, "total_power_w")
    fans = values(samples, "fan_speed_rpm")
    recoveries = values(samples, "gpu_recovery_count")
    thermal_abort = any(bool(sample.get("thermal_abort")) for sample in samples)
    passed = bool(reports) and all(report.get("passed") for report in reports) and not thermal_abort
    compute_devices = sorted(
        {
            str(device)
            for report in reports
            for device in report.get("compute_devices", [])
        }
    )
    accelerated_devices = sorted(
        {
            str(report["accelerated_device"])
            for report in reports
            if report.get("accelerated_device")
        }
    )

    lines = [
        "# Core ML最小ビルド実測レポート",
        "",
        f"- Git commit: `{args.git_commit}`",
        f"- 総合結果: **{'PASS' if passed else 'FAIL'}**",
        f"- Thermal guard: {args.thermal_limit_c} °C",
        f"- Thermal abort: {'あり' if thermal_abort else 'なし'}",
        f"- GPU温度: {range_text(temperatures, ' °C')}",
        f"- GPU activity: {range_text(activities, ' %')}",
        f"- GPU power: {range_text(powers, ' W')}",
        f"- GPU fan: {range_text(fans, ' RPM')}",
        f"- GPU recovery count: {range_text(recoveries)}",
        "- CPU温度: CLIから取得できないため未記録",
        "",
        "## Apple演算stack",
        "",
        f"- Core ML compute devices: {', '.join(compute_devices) or '取得不可'}",
        f"- Metal device: {', '.join(accelerated_devices) or '取得不可'}",
        f"- Metal 3: {'yes' if reports and all(report.get('metal3') for report in reports) else 'no'}",
        f"- MPS: {'PASS' if reports and all(report.get('mps_supported') and report.get('mps_max_abs_error', 1) <= 1e-6 for report in reports) else 'FAIL'}",
        f"- Accelerate/vDSP: {'PASS' if reports and all(report.get('accelerate_passed') for report in reports) else 'FAIL'}",
        "",
        "## Core ML結果",
        "",
        "| profile | compute units | batch | iterations | max abs error | p50 ms | p95 ms | PASS |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for report in reports:
        row = {**report, "passed_text": "yes" if report.get("passed") else "no"}
        lines.append(
            "| {profile} | {compute_units} | {batch_size} | {iterations} | "
            "{max_abs_error:.8f} | {p50_ms:.4f} | {p95_ms:.4f} | {passed_text} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 注記",
            "",
            "- FAM信号、router replay、実weight MoEは未接続。",
            "- `cpuAndGPU`はGPU使用を許可する指定であり、全operationのGPU配置を保証しない。",
            "- GPU温度・電力・fanはAMD driverのIORegistry `PerformanceStatistics`から取得。",
            "- このレポートのPASSを確認した地点で一旦停止し、FAM結合は別工程とする。",
            "",
        ]
    )
    (args.run_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
