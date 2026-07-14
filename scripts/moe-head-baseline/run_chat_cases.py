#!/usr/bin/env python3
"""固定fixtureをllama-serverへ送り、応答と判定をcaseごとに逐次保存する。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


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


def request_json(url: str, payload: dict[str, Any] | None, timeout: float) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            decoded: dict[str, Any] = json.loads(body) if body else {}
        except json.JSONDecodeError:
            decoded = {"raw_body": body}
        return error.code, decoded


def wait_until_ready(base_url: str, server_pid: int, timeout_seconds: float) -> dict[str, Any]:
    started = time.monotonic()
    attempts = 0
    last_status: int | None = None
    last_payload: dict[str, Any] = {}
    while time.monotonic() - started < timeout_seconds:
        if not process_alive(server_pid):
            raise RuntimeError("llama-serverがhealth check完了前に終了しました")
        attempts += 1
        try:
            last_status, last_payload = request_json(f"{base_url}/health", None, 5.0)
            if last_status == 200 and last_payload.get("status") == "ok":
                return {
                    "ready": True,
                    "attempts": attempts,
                    "elapsed_seconds": time.monotonic() - started,
                    "status_code": last_status,
                    "health": last_payload,
                }
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(1.0)
    raise TimeoutError(
        f"health checkが{timeout_seconds:.0f}秒以内に完了しませんでした"
        f" (last_status={last_status}, last_payload={last_payload})"
    )


def response_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    message = choices[0].get("message")
    return message if isinstance(message, dict) else {}


def evaluate(assertion: dict[str, Any], response: dict[str, Any]) -> tuple[bool, str]:
    message = response_message(response)
    kind = assertion.get("kind")
    content = message.get("content")
    content_text = content if isinstance(content, str) else ""
    if kind == "non_empty_japanese_content":
        passed = bool(content_text.strip()) and bool(re.search(r"[ぁ-んァ-ヶ一-龯]", content_text))
        return passed, "日本語応答あり" if passed else "日本語contentが空です"
    if kind == "content_contains":
        expected = str(assertion.get("value", ""))
        passed = expected in content_text
        return passed, f"期待文字列『{expected}』を確認" if passed else f"期待文字列『{expected}』がありません"
    if kind == "tool_call":
        expected_name = assertion.get("function_name")
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            return False, "tool_callsが1件ではありません"
        choices = response.get("choices")
        finish_reason = choices[0].get("finish_reason") if isinstance(choices, list) and choices else None
        if finish_reason != "tool_calls":
            return False, "finish_reasonがtool_callsではありません"
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
                return False, "tool call typeがfunctionではありません"
            function = tool_call.get("function") if isinstance(tool_call, dict) else None
            if not isinstance(function, dict) or function.get("name") != expected_name:
                continue
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    return False, "tool argumentが有効なJSONではありません"
            argument_key = str(assertion.get("argument_key", "city"))
            expected_argument = str(assertion.get("argument_contains", ""))
            argument_value = arguments.get(argument_key) if isinstance(arguments, dict) else None
            if (
                isinstance(argument_value, str)
                and argument_value
                and (not expected_argument or expected_argument in argument_value)
            ):
                return True, f"{expected_name} tool callを確認"
        return False, f"{expected_name} tool callまたは期待argumentがありません"
    return False, f"未知のassertionです: {kind}"


def message_hash(message: dict[str, Any]) -> str:
    canonical = json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--health-timeout-seconds", type=float, default=600.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=300.0)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started_utc = datetime.now(timezone.utc).isoformat()
    summary: dict[str, Any] = {
        "kind": "moe_upstream_chat_baseline",
        "started_utc": started_utc,
        "health": None,
        "cases": [],
        "all_passed": False,
    }
    atomic_write_json(args.output_dir / "summary.json", summary)

    try:
        summary["health"] = wait_until_ready(
            args.base_url.rstrip("/"), args.server_pid, args.health_timeout_seconds
        )
        atomic_write_json(args.output_dir / "summary.json", summary)
    except (RuntimeError, TimeoutError) as error:
        summary["fatal_error_ja"] = str(error)
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(args.output_dir / "summary.json", summary)
        print(f"停止: {error}", file=os.sys.stderr)
        return 1

    generation = fixture["generation"]
    model_alias = fixture["model_alias"]
    for case in fixture["cases"]:
        case_id = case["id"]
        request_payload: dict[str, Any] = {
            "model": model_alias,
            "messages": case["messages"],
            "temperature": generation["temperature"],
            "seed": generation["seed"],
            "max_tokens": generation["max_tokens"],
            "stream": False,
            "cache_prompt": False,
            "n": 1,
            "top_k": 1,
            "top_p": 1.0,
            "min_p": 0.0,
        }
        if "tools" in case:
            request_payload["tools"] = case["tools"]
            request_payload["tool_choice"] = case.get("tool_choice", "required")
            request_payload["parallel_tool_calls"] = False
        atomic_write_json(args.output_dir / f"request-{case_id}.json", request_payload)

        case_started = time.monotonic()
        try:
            status_code, response = request_json(
                f"{args.base_url.rstrip('/')}/v1/chat/completions",
                request_payload,
                args.request_timeout_seconds,
            )
            atomic_write_json(args.output_dir / f"response-{case_id}.json", response)
            passed, assertion_message = evaluate(case["assertion"], response) if status_code == 200 else (
                False,
                f"HTTP status {status_code}",
            )
            message = response_message(response)
            choice = response.get("choices", [{}])[0] if isinstance(response.get("choices"), list) and response.get("choices") else {}
            result = {
                "id": case_id,
                "description_ja": case["description_ja"],
                "status_code": status_code,
                "elapsed_seconds": time.monotonic() - case_started,
                "passed": passed,
                "assertion_message_ja": assertion_message,
                "finish_reason": choice.get("finish_reason") if isinstance(choice, dict) else None,
                "response_message_sha256": message_hash(message) if message else None,
                "usage": response.get("usage"),
                "timings": response.get("timings"),
            }
        except (OSError, ValueError, json.JSONDecodeError) as error:
            result = {
                "id": case_id,
                "description_ja": case["description_ja"],
                "elapsed_seconds": time.monotonic() - case_started,
                "passed": False,
                "assertion_message_ja": f"request失敗: {error}",
            }
            atomic_write_json(args.output_dir / f"response-{case_id}.json", {"error_ja": str(error)})

        summary["cases"].append(result)
        atomic_write_json(args.output_dir / "summary.json", summary)
        print(f"{case_id}: {'PASS' if result['passed'] else 'FAIL'} - {result['assertion_message_ja']}")
        if not process_alive(args.server_pid):
            break

    summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
    summary["all_passed"] = (
        len(summary["cases"]) == len(fixture["cases"])
        and all(case["passed"] for case in summary["cases"])
    )
    atomic_write_json(args.output_dir / "summary.json", summary)
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    raise SystemExit(main())
