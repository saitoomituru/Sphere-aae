"""Environment variables used by the Astro Agent Edge (AAE)."""

import os
import sys
from pathlib import Path
from typing import List

SPHERE_AAE_CHAT_CONFIG_VERSION = "0.1.0"


def _check():
    if SPHERE_AAE_JIT_POLICY not in ["ON", "OFF", "REDO", "READONLY"]:
        raise ValueError(
            'Invalid SPHERE_AAE_JIT_POLICY. It has to be one of "ON", "OFF", "REDO", "READONLY"'
            f"but got {SPHERE_AAE_JIT_POLICY}."
        )

    if SPHERE_AAE_DOWNLOAD_CACHE_POLICY not in ["ON", "OFF", "REDO", "READONLY"]:
        raise ValueError(
            "Invalid SPHERE_AAE_AUTO_DOWNLOAD_POLICY. "
            'It has to be one of "ON", "OFF", "REDO", "READONLY"'
            f"but got {SPHERE_AAE_DOWNLOAD_CACHE_POLICY}."
        )


def _get_cache_dir() -> Path:
    if "SPHERE_AAE_HOME" in os.environ:
        result = Path(os.environ["SPHERE_AAE_HOME"])
    elif sys.platform == "win32":
        result = Path(os.environ["LOCALAPPDATA"])
        result = result / "sphere_aae"
    elif os.getenv("XDG_CACHE_HOME", None) is not None:
        result = Path(os.getenv("XDG_CACHE_HOME"))
        result = result / "sphere_aae"
    else:
        result = Path(os.path.expanduser("~/.cache"))
        result = result / "sphere_aae"
    result.mkdir(parents=True, exist_ok=True)
    if not result.is_dir():
        raise ValueError(
            f"The default cache directory is not a directory: {result}. "
            "Use environment variable SPHERE_AAE_HOME to specify a valid cache directory."
        )
    (result / "model_weights").mkdir(parents=True, exist_ok=True)
    (result / "model_lib").mkdir(parents=True, exist_ok=True)
    return result


def _get_dso_suffix() -> str:
    if "SPHERE_AAE_DSO_SUFFIX" in os.environ:
        return os.environ["SPHERE_AAE_DSO_SUFFIX"]
    if sys.platform == "win32":
        return "dll"
    if sys.platform == "darwin":
        return "dylib"
    return "so"


def _get_test_model_path() -> List[Path]:
    paths = []
    if "SPHERE_AAE_TEST_MODEL_PATH" in os.environ:
        paths += [Path(p) for p in os.environ["SPHERE_AAE_TEST_MODEL_PATH"].split(os.pathsep)]
    # by default, we reuse the cache dir via sphere_aae chat
    # note that we do not auto download for testcase
    # to avoid networking dependencies
    base_list = ["hf"]
    paths += [_get_cache_dir() / "model_weights" / base / "sphere-aae" for base in base_list] + [
        Path(os.path.abspath(os.path.curdir)),
        Path(os.path.abspath(os.path.curdir)) / "dist",
    ]
    return paths


def _get_read_only_weight_caches() -> List[Path]:
    if "SPHERE_AAE_READONLY_WEIGHT_CACHE" in os.environ:
        return [Path(p) for p in os.environ["SPHERE_AAE_READONLY_WEIGHT_CACHE"].split(os.pathsep)]
    return []


SPHERE_AAE_TEMP_DIR = os.getenv("SPHERE_AAE_TEMP_DIR", None)
SPHERE_AAE_MULTI_ARCH = os.environ.get("SPHERE_AAE_MULTI_ARCH", None)
SPHERE_AAE_JIT_POLICY = os.environ.get("SPHERE_AAE_JIT_POLICY", "ON")
SPHERE_AAE_DSO_SUFFIX = _get_dso_suffix()
SPHERE_AAE_TEST_MODEL_PATH: List[Path] = _get_test_model_path()

SPHERE_AAE_DOWNLOAD_CACHE_POLICY = os.environ.get("SPHERE_AAE_DOWNLOAD_CACHE_POLICY", "ON")
SPHERE_AAE_HOME: Path = _get_cache_dir()
SPHERE_AAE_READONLY_WEIGHT_CACHE = _get_read_only_weight_caches()

_check()
