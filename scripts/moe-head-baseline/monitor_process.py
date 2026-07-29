#!/usr/bin/env python3
"""対象processのCPU使用率とmemoryをJSONLへ逐次保存する。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    result = subprocess.run(
        ["ps", "-o", "state=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    state = result.stdout.strip()
    return result.returncode == 0 and bool(state) and not state.startswith("Z")


def read_process(pid: int) -> dict[str, object] | None:
    result = subprocess.run(
        ["ps", "-o", "pid=,%cpu=,rss=,vsz=,etime=,state=", "-p", str(pid)],
        check=False,
        capture_output=True,
        text=True,
    )
    line = result.stdout.strip()
    if result.returncode != 0 or not line:
        return None
    fields = line.split(maxsplit=5)
    if len(fields) != 6:
        return None
    process_id, cpu_percent, rss_kib, vsz_kib, elapsed, state = fields
    return {
        "pid": int(process_id),
        "cpu_percent": float(cpu_percent),
        "rss_kib": int(rss_kib),
        "vsz_kib": int(vsz_kib),
        "elapsed": elapsed,
        "state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--max-samples", type=int, default=3600)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sample_count = 0
    with args.output.open("w", encoding="utf-8") as stream:
        for sample_index in range(args.max_samples):
            process = read_process(args.pid)
            if process is None:
                if process_alive(args.pid):
                    return 3
                return 0 if sample_count else 3
            if str(process["state"]).startswith("Z"):
                return 0 if sample_count else 3
            sample = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "monotonic_seconds": time.monotonic(),
                "sample_index": sample_index,
                "load_average": list(os.getloadavg()),
                **process,
            }
            stream.write(json.dumps(sample, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            sample_count += 1
            time.sleep(args.interval)
    if not sample_count:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
