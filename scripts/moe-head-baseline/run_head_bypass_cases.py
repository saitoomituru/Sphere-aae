#!/usr/bin/env python3
"""同一serverの応答をHEAD実行前後で比較し、FAM未接続を検証する。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_chat_cases import (
    atomic_write_json,
    evaluate,
    message_hash,
    process_alive,
    request_json,
    response_message,
    wait_until_ready,
)


def atomic_write_text(path: Path, text: str) -> None:
    """textを一時fileへfsyncしてから目的pathへ置き換える。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(text)
        if text and not text.endswith("\n"):
            stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def canonical_message(message: dict[str, Any]) -> str:
    """messageをkey順と最小separatorで正規化する。"""

    return json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sanitized_text(value: str | bytes | None, repo_root: Path) -> str:
    """保存前にrepository rootとHOMEの絶対pathを伏せる。"""

    if value is None:
        result = ""
    elif isinstance(value, bytes):
        result = value.decode("utf-8", errors="replace")
    else:
        result = value

    replacements: dict[str, str] = {
        str(repo_root.resolve()): "<REPO_ROOT>",
        str(Path.home().resolve()): "<HOME>",
    }
    environment_home = os.environ.get("HOME")
    if environment_home:
        replacements[str(Path(environment_home).expanduser().resolve())] = "<HOME>"
    for original in sorted(replacements, key=len, reverse=True):
        if original:
            result = result.replace(original, replacements[original])
    return result


def health_check(
    base_url: str,
    server_pid: int,
    timeout_seconds: float,
    label: str,
) -> dict[str, Any]:
    """server生存とhealth status=okを一度だけ確認する。"""

    result: dict[str, Any] = {
        "label": label,
        "server_alive": process_alive(server_pid),
        "status_code": None,
        "status": None,
        "passed": False,
    }
    if not result["server_alive"]:
        result["message_ja"] = "llama-serverが終了しています"
        return result
    try:
        status_code, payload = request_json(
            f"{base_url.rstrip('/')}/health",
            None,
            min(timeout_seconds, 10.0),
        )
        result["status_code"] = status_code
        result["status"] = payload.get("status")
        result["passed"] = status_code == 200 and payload.get("status") == "ok"
        result["message_ja"] = (
            "health status=okを確認"
            if result["passed"]
            else f"health check不一致: HTTP {status_code}, status={payload.get('status')}"
        )
    except Exception as error:  # health失敗もsummaryへ残すため、この段階では送出しない。
        result["message_ja"] = f"health check失敗: {error}"
    return result


def build_request(case: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    """上流baselineと同じ決定的chat requestを構成する。"""

    generation = fixture["generation"]
    return {
        "model": fixture["model_alias"],
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


def run_response(
    *,
    label: str,
    request_payload: dict[str, Any],
    base_url: str,
    server_pid: int,
    timeout_seconds: float,
    output_dir: Path,
    summary: dict[str, Any],
) -> tuple[dict[str, Any], str | None]:
    """一回のchat応答を保存し、日本語contentとHTTP statusを判定する。"""

    key = label.lower()
    atomic_write_json(output_dir / f"request-{key}.json", request_payload)
    health = health_check(base_url, server_pid, timeout_seconds, f"{label}実行前")
    summary["health_checks"].append(health)
    atomic_write_json(output_dir / "summary.json", summary)

    started = time.monotonic()
    status_code: int | None = None
    response: dict[str, Any] = {}
    error_ja: str | None = None
    if not health["passed"]:
        error_ja = str(health["message_ja"])
    else:
        try:
            status_code, response = request_json(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                request_payload,
                timeout_seconds,
            )
        except Exception as error:  # timeoutや接続断もcase単位で保存する。
            error_ja = f"request失敗: {error}"

    if error_ja is not None:
        response = {"error_ja": error_ja}
    atomic_write_json(output_dir / f"response-{key}.json", response)

    message = response_message(response) if status_code == 200 else {}
    japanese_passed, assertion_message = (
        evaluate({"kind": "non_empty_japanese_content"}, response)
        if status_code == 200
        else (False, error_ja or f"HTTP status {status_code}")
    )
    canonical = canonical_message(message) if message else None
    result: dict[str, Any] = {
        "status_code": status_code,
        "elapsed_seconds": time.monotonic() - started,
        "http_200": status_code == 200,
        "japanese_non_empty": japanese_passed,
        "passed": status_code == 200 and japanese_passed,
        "assertion_message_ja": assertion_message,
        "canonical_message_sha256": message_hash(message) if message else None,
    }
    summary["responses"][key] = result
    atomic_write_json(output_dir / "summary.json", summary)
    print(f"{label}: {'PASS' if result['passed'] else 'FAIL'} - {assertion_message}")
    return message, canonical


def run_head(
    *,
    executable: Path,
    model: Path,
    fixture: Path,
    output_dir: Path,
    timeout_seconds: float,
    repo_root: Path,
) -> dict[str, Any]:
    """HEADを別processで実行し、FAM未接続fieldを厳密に判定する。"""

    temporary_result = output_dir / f".head-result-executable-{os.getpid()}.json"
    temporary_result.unlink(missing_ok=True)
    stdout = ""
    stderr = ""
    return_code: int | None = None
    timed_out = False
    execution_error_ja: str | None = None
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [
                str(executable),
                "--model",
                str(model),
                "--fixture",
                str(fixture),
                "--json-output",
                str(temporary_result),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = sanitized_text(error.stdout, repo_root)
        stderr = sanitized_text(error.stderr, repo_root)
        execution_error_ja = f"HEAD実行が{timeout_seconds:.0f}秒でtimeoutしました"
    except OSError as error:
        execution_error_ja = f"HEAD processを起動できません: {error}"
        stderr = str(error)
    finally:
        atomic_write_text(output_dir / "head-stdout.txt", sanitized_text(stdout, repo_root))
        atomic_write_text(output_dir / "head-stderr.txt", sanitized_text(stderr, repo_root))

    head_payload: dict[str, Any]
    result_available = temporary_result.is_file()
    if result_available:
        try:
            decoded = json.loads(temporary_result.read_text(encoding="utf-8"))
            if not isinstance(decoded, dict):
                raise ValueError("HEAD resultのrootがobjectではありません")
            head_payload = decoded
        except (OSError, ValueError, json.JSONDecodeError) as error:
            execution_error_ja = execution_error_ja or f"HEAD resultを読めません: {error}"
            head_payload = {"error_ja": sanitized_text(str(error), repo_root)}
    else:
        head_payload = {
            "error_ja": sanitized_text(
                execution_error_ja or "HEAD resultが作成されませんでした", repo_root
            )
        }
    atomic_write_json(output_dir / "head-result.json", head_payload)
    temporary_result.unlink(missing_ok=True)

    checks = {
        "process_exit_zero": return_code == 0,
        "result_passed": head_payload.get("passed") is True,
        "fam_disabled": head_payload.get("fam_enabled") is False,
        "input_zero": head_payload.get("input_mode") == "zero",
        "input_all_zero": head_payload.get("input_all_zero") is True,
        "override_disabled": head_payload.get("router_override_applied") is False,
        "observe_only": head_payload.get("head_mode") == "observe_only",
        "cpu_only": head_payload.get("compute_units") == "cpuOnly",
        "logits_finite": head_payload.get("logits_finite") is True,
        "output_shape_matches": head_payload.get("output_shape_matches") is True,
        "repeat_matches": head_payload.get("deterministic_repeat_match") is True,
        "top_k_matches": head_payload.get("top_k_match") is True,
    }
    passed = not timed_out and all(checks.values())
    result: dict[str, Any] = {
        "exit_code": return_code,
        "elapsed_seconds": time.monotonic() - started,
        "timed_out": timed_out,
        "result_available": result_available,
        **checks,
        "passed": passed,
    }
    if execution_error_ja:
        result["error_ja"] = sanitized_text(execution_error_ja, repo_root)
    return result


def selected_case(fixture: dict[str, Any]) -> dict[str, Any]:
    """japanese_general caseを一意に選ぶ。"""

    matches = [case for case in fixture.get("cases", []) if case.get("id") == "japanese_general"]
    if len(matches) != 1:
        raise ValueError("fixture内のjapanese_general caseは1件でなければなりません")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="FAM未接続HEAD前後の決定的応答を比較します")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--server-pid", type=int, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--head-executable",
        "--head-binary",
        dest="head_executable",
        type=Path,
        required=True,
    )
    parser.add_argument("--head-model", type=Path, required=True)
    parser.add_argument("--head-fixture", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--health-timeout-seconds", type=float, default=600.0)
    parser.add_argument("--request-timeout-seconds", type=float, default=300.0)
    parser.add_argument("--head-timeout-seconds", type=float, default=120.0)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "kind": "moe_head_bypass_comparison",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "health_checks": [],
        "responses": {"a1": None, "a2": None, "b": None},
        "head": None,
        "a1_a2_match": False,
        "a1_b_match": False,
        "a2_b_match": False,
        "all_responses_match": False,
        "server_alive_final": False,
        "all_passed": False,
    }
    atomic_write_json(args.output_dir / "summary.json", summary)
    atomic_write_text(args.output_dir / "head-stdout.txt", "")
    atomic_write_text(args.output_dir / "head-stderr.txt", "")
    atomic_write_json(
        args.output_dir / "head-result.json",
        {"status": "not_run", "message_ja": "HEADはまだ実行されていません"},
    )

    canonical: dict[str, str | None] = {"a1": None, "a2": None, "b": None}
    try:
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        case = selected_case(fixture)
        request_payload = build_request(case, fixture)

        initial = wait_until_ready(
            args.base_url.rstrip("/"),
            args.server_pid,
            args.health_timeout_seconds,
        )
        summary["initial_health"] = initial
        atomic_write_json(args.output_dir / "summary.json", summary)

        for label in ("A1", "A2"):
            _, canonical[label.lower()] = run_response(
                label=label,
                request_payload=request_payload,
                base_url=args.base_url,
                server_pid=args.server_pid,
                timeout_seconds=args.request_timeout_seconds,
                output_dir=args.output_dir,
                summary=summary,
            )

        head_precheck = health_check(
            args.base_url,
            args.server_pid,
            args.request_timeout_seconds,
            "HEAD実行前",
        )
        summary["health_checks"].append(head_precheck)
        if head_precheck["passed"]:
            summary["head"] = run_head(
                executable=args.head_executable,
                model=args.head_model,
                fixture=args.head_fixture,
                output_dir=args.output_dir,
                timeout_seconds=args.head_timeout_seconds,
                repo_root=args.repo_root,
            )
        else:
            message = str(head_precheck["message_ja"])
            atomic_write_text(args.output_dir / "head-stdout.txt", "")
            atomic_write_text(args.output_dir / "head-stderr.txt", message)
            atomic_write_json(args.output_dir / "head-result.json", {"error_ja": message})
            summary["head"] = {"passed": False, "error_ja": message}
        atomic_write_json(args.output_dir / "summary.json", summary)
        print(f"HEAD: {'PASS' if summary['head']['passed'] else 'FAIL'}")

        _, canonical["b"] = run_response(
            label="B",
            request_payload=request_payload,
            base_url=args.base_url,
            server_pid=args.server_pid,
            timeout_seconds=args.request_timeout_seconds,
            output_dir=args.output_dir,
            summary=summary,
        )

        summary["a1_a2_match"] = canonical["a1"] is not None and canonical["a1"] == canonical["a2"]
        summary["a1_b_match"] = canonical["a1"] is not None and canonical["a1"] == canonical["b"]
        summary["a2_b_match"] = canonical["a2"] is not None and canonical["a2"] == canonical["b"]
        summary["all_responses_match"] = (
            summary["a1_a2_match"]
            and summary["a1_b_match"]
            and summary["a2_b_match"]
        )
        summary["comparison_message_ja"] = (
            "A1、A2、Bのcanonical messageが一致しました"
            if summary["all_responses_match"]
            else "A1、A2、Bのcanonical messageに差があります"
        )
    except Exception as error:  # 途中結果をsummaryへ残したうえでFAILにする。
        summary["fatal_error_ja"] = sanitized_text(str(error), args.repo_root)
        print(f"停止: {summary['fatal_error_ja']}", file=os.sys.stderr)
    finally:
        final_health = health_check(
            args.base_url,
            args.server_pid,
            args.request_timeout_seconds,
            "全比較完了時",
        )
        summary["health_checks"].append(final_health)
        summary["server_alive_final"] = process_alive(args.server_pid)
        response_results = list(summary["responses"].values())
        summary["all_passed"] = (
            "fatal_error_ja" not in summary
            and all(isinstance(item, dict) and item.get("passed") is True for item in response_results)
            and isinstance(summary.get("head"), dict)
            and summary["head"].get("passed") is True
            and summary["all_responses_match"]
            and all(check.get("passed") is True for check in summary["health_checks"])
            and summary["server_alive_final"]
        )
        summary["finished_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(args.output_dir / "summary.json", summary)

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
