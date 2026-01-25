# pylint: disable=missing-module-docstring,missing-function-docstring
import os
from typing import Tuple

import pytest

from sphere_aae.serve import PopenServer


@pytest.fixture(scope="session")
def served_model() -> Tuple[str, str]:
    model_lib = os.environ.get("SPHERE_AAE_SERVE_MODEL_LIB")
    if model_lib is None:
        pytest.skip(
            'Environment variable "SPHERE_AAE_SERVE_MODEL_LIB" not found. '
            "MLC サーバーテストをスキップします。"
        )
    model = os.path.dirname(model_lib)
    return model, model_lib


@pytest.fixture(scope="session")
def launch_server(served_model):  # pylint: disable=redefined-outer-name
    """A pytest session-level fixture which launches the server in a subprocess."""
    server = PopenServer(
        model=served_model[0],
        model_lib=served_model[1],
        enable_tracing=True,
        enable_debug=True,
        port=8000,
    )

    with server:
        yield
