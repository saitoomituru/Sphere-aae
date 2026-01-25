# pylint: disable=missing-docstring
from pathlib import Path
from typing import Union

import pytest
import tvm

from sphere_aae.loader import HuggingFaceLoader
from sphere_aae.model import MODEL_PRESETS, MODELS
from sphere_aae.quantization import QUANTIZATION
from sphere_aae.support import logging, tqdm

logging.enable_logging()


@pytest.mark.parametrize(
    "param_path",
    [
        "./dist/models/llama-2-7b-w4-g128-awq.pt",
        "./dist/models/Llama-2-7B-AWQ/model.safetensors",
    ],
)
def test_load_llama(param_path: Union[str, Path]):
    path_params = Path(param_path)
    if not path_params.exists():
        pytest.skip(f"Model file not found: {path_params}")

    model = MODELS["llama"]
    quantization = QUANTIZATION["q4f16_awq"]
    config = model.config.from_dict(MODEL_PRESETS["llama2_7b"])
    loader = HuggingFaceLoader(
        path=path_params,
        extern_param_map=model.source["awq"](config, quantization),
    )
    with tqdm.redirect():
        for _name, _param in loader.load(tvm.device("cpu")):
            ...


if __name__ == "__main__":
    test_load_llama(param_path="./dist/models/llama-2-7b-w4-g128-awq.pt")
    test_load_llama(param_path="./dist/models/Llama-2-7B-AWQ/model.safetensors")
