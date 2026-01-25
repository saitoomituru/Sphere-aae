"""Extra utilities to mark tests"""

import functools
import inspect
from pathlib import Path
from typing import Callable

import pytest

from sphere_aae.support.constants import SPHERE_AAE_TEST_MODEL_PATH


def require_test_model(*models: str):
    """Testcase decorator to require a model

    Examples
    --------
    .. code::

        @require_test_model("Llama-2-7b-chat-hf-q4f16_1-AAE")
        def test_reload_reset_unload(model):
            # model now points to the right path
            # specified by SPHERE_AAE_TEST_MODEL_PATH
            engine = sphere_aae.SphereAaeEngine(model)
            # test code follows

    Parameters
    ----------
    models : List[str]
        The model directories or URLs.
    """
    model_paths = []
    missing_models = []

    for model in models:
        model_path = None
        for base_path in SPHERE_AAE_TEST_MODEL_PATH:
            if (base_path / model / "sphere-aae-chat-config.json").is_file():
                model_path = base_path / model
                break
        if model_path is None and (Path(model) / "sphere-aae-chat-config.json").is_file():
            model_path = Path(model)

        if model_path is None:
            missing_models.append(model)
        else:
            model_paths.append(str(model_path))

    message = (
        f"Model {', '.join(missing_models)} not found in candidate paths "
        f"{[str(p) for p in SPHERE_AAE_TEST_MODEL_PATH]},"
        " if you set SPHERE_AAE_TEST_MODEL_PATH, please ensure model paths are in the right location,"
        " by default we reuse cache, try to run sphere_aae chat to download right set of models."
    )

    def _decorator(func: Callable[..., None]):
        wrapped = functools.partial(func, *model_paths)
        wrapped.__name__ = func.__name__  # type: ignore

        if inspect.iscoroutinefunction(wrapped):
            # The function is a coroutine function ("async def func(...)")
            @functools.wraps(wrapped)
            async def wrapper(*args, **kwargs):
                if len(missing_models) > 0:
                    print(f"{message} skipping...")
                    return
                await wrapped(*args, **kwargs)

        else:
            # The function is a normal function ("def func(...)")
            @functools.wraps(wrapped)
            def wrapper(*args, **kwargs):
                if len(missing_models) > 0:
                    print(f"{message} skipping...")
                    return
                wrapped(*args, **kwargs)

        return pytest.mark.skipif(len(missing_models) > 0, reason=message)(wrapper)

    return _decorator


def require_test_tokenizers(*models: str):
    """Testcase decorator to require a path to tokenizers"""
    # redirect to require models for now
    return require_test_model(*models)
