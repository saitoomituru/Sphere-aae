#!/usr/bin/env python3
"""Record AMD GPU telemetry from IORegistry and guard a workload by temperature."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KEYS = {
    "Temperature(C)": "temperature_c",
    "GPU Activity(%)": "gpu_activity_percent",
    "Device Utilization %": "device_utilization_percent",
    "Fan Speed(RPM)": "fan_speed_rpm",
    "Fan Speed(%)": "fan_speed_percent",
    "Total Power(W)": "total_power_w",
    "Core Clock(MHz)": "core_clock_mhz",
    "Memory Clock(MHz)": "memory_clock_mhz",
    "inUseVidMemoryBytes": "vram_used_bytes",
    "vramFreeBytes": "vram_free_bytes",
    "recoveryCount": "gpu_recovery_count",
}


def process_alive(pid: int | None) -> bool:
    if pid is None:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    process = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    state = process.stdout.strip()
    return process.returncode == 0 and bool(state) and not state.startswith("Z")


def read_gpu_stats() -> dict[str, Any]:
    result = subprocess.run(
        ["ioreg", "-l", "-w0", "-r", "-k", "PerformanceStatistics"],
        check=False,
        capture_output=True,
        text=True,
    )
    line = next(
        (item for item in result.stdout.splitlines() if '"PerformanceStatistics" =' in item),
        "",
    )
    stats: dict[str, Any] = {
        "ioreg_returncode": result.returncode,
        "telemetry_available": bool(line),
    }
    for source_key, output_key in KEYS.items():
        match = re.search(rf'"{re.escape(source_key)}"=(-?\d+)', line)
        stats[output_key] = int(match.group(1)) if match else None
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--watch-pid", type=int)
    parser.add_argument("--max-temperature-c", type=int, default=80)
    parser.add_argument("--max-samples", type=int, default=3600)
    parser.add_argument("--require-telemetry", action="store_true")
    parser.add_argument("--fail-on-sample-limit", action="store_true")
    args = parser.parse_args()
    if args.max_samples <= 0:
        parser.error("--max-samplesは正数で指定してください")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    thermal_abort = False
    telemetry_abort = False
    sample_limit_abort = False
    with args.output.open("w", encoding="utf-8") as stream:
        for sample_index in range(args.max_samples):
            if sample_index > 0 and not process_alive(args.watch_pid):
                break
            sample = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "monotonic_seconds": time.monotonic(),
                "sample_index": sample_index,
                "load_average": list(os.getloadavg()),
                "cpu_temperature_c": None,
                **read_gpu_stats(),
            }
            temperature = sample.get("temperature_c")
            if args.require_telemetry and (
                not sample.get("telemetry_available")
                or temperature is None
                or sample.get("gpu_recovery_count") is None
            ):
                sample["telemetry_abort"] = True
                sample["thermal_abort"] = False
                telemetry_abort = True
                if args.watch_pid is not None and process_alive(args.watch_pid):
                    os.kill(args.watch_pid, signal.SIGTERM)
            elif temperature is not None and temperature >= args.max_temperature_c:
                sample["thermal_abort"] = True
                sample["telemetry_abort"] = False
                thermal_abort = True
                if args.watch_pid is not None and process_alive(args.watch_pid):
                    os.kill(args.watch_pid, signal.SIGTERM)
            else:
                sample["thermal_abort"] = False
                sample["telemetry_abort"] = False
            sample["sample_limit_abort"] = False
            if (
                not thermal_abort
                and not telemetry_abort
                and args.fail_on_sample_limit
                and sample_index + 1 >= args.max_samples
                and args.watch_pid is not None
                and process_alive(args.watch_pid)
            ):
                sample["sample_limit_abort"] = True
                sample_limit_abort = True
                os.kill(args.watch_pid, signal.SIGTERM)
            stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            if thermal_abort or telemetry_abort or sample_limit_abort:
                break
            time.sleep(args.interval)
    if sample_limit_abort:
        return 77
    if telemetry_abort:
        return 76
    return 75 if thermal_abort else 0


if __name__ == "__main__":
    raise SystemExit(main())
