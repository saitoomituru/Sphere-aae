"""Help function for detecting the model configuration file `config.json`"""

import json
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from . import logging
from .style import bold, green

if TYPE_CHECKING:
    from sphere_aae.model import Model  # pylint: disable=unused-import
    from sphere_aae.quantization import Quantization  # pylint: disable=unused-import


logger = logging.getLogger(__name__)

FOUND = green("Found")


def detect_sphere_aae_chat_config(sphere_aae_chat_config: str) -> Path:
    """Detect and return the path that points to sphere-aae-chat-config.json.
    If `sphere_aae_chat_config` is a directory, it looks for sphere-aae-chat-config.json below it.

    Parameters
    ---------
    sphere_aae_chat_config : str
        The path to `sphere-aae-chat-config.json`, or the directory containing
        `sphere-aae-chat-config.json`.

    Returns
    -------
    sphere_aae_chat_config_json_path : pathlib.Path
        The path points to sphere_aae_chat_config.json.
    """
    # pylint: disable=import-outside-toplevel
    from sphere_aae.model import MODEL_PRESETS

    from .download_cache import download_and_cache_sphere_aae_weights

    # pylint: enable=import-outside-toplevel

    if sphere_aae_chat_config.startswith("HF://") or sphere_aae_chat_config.startswith("http"):
        sphere_aae_chat_config_path = Path(download_and_cache_sphere_aae_weights(model_url=sphere_aae_chat_config))
    elif isinstance(sphere_aae_chat_config, str) and sphere_aae_chat_config in MODEL_PRESETS:
        logger.info("%s sphere-aae preset model: %s", FOUND, sphere_aae_chat_config)
        content = MODEL_PRESETS[sphere_aae_chat_config].copy()
        content["model_preset_tag"] = sphere_aae_chat_config
        temp_file = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            suffix=".json",
            delete=False,
        )
        logger.info("Dumping config to: %s", temp_file.name)
        sphere_aae_chat_config_path = Path(temp_file.name)
        with sphere_aae_chat_config_path.open("w", encoding="utf-8") as sphere_aae_chat_config_file:
            json.dump(content, sphere_aae_chat_config_file, indent=2)
    else:
        sphere_aae_chat_config_path = Path(sphere_aae_chat_config)
    if not sphere_aae_chat_config_path.exists():
        raise ValueError(f"{sphere_aae_chat_config_path} does not exist.")

    if sphere_aae_chat_config_path.is_dir():
        # search sphere-aae-chat-config.json under path
        sphere_aae_chat_config_json_path = sphere_aae_chat_config_path / "sphere-aae-chat-config.json"
        if not sphere_aae_chat_config_json_path.exists():
            raise ValueError(f"Fail to find sphere-aae-chat-config.json under {sphere_aae_chat_config_path}.")
    else:
        sphere_aae_chat_config_json_path = sphere_aae_chat_config_path

    logger.info("%s model configuration: %s", FOUND, sphere_aae_chat_config_json_path)
    return sphere_aae_chat_config_json_path


def detect_config(config: str) -> Path:
    """Detect and return the path that points to config.json. If `config` is a directory,
    it looks for config.json below it.

    Parameters
    ---------
    config : str
        The preset name of the model, or the path to `config.json`, or the directory containing
        `config.json`.

    Returns
    -------
    config_json_path : pathlib.Path
        The path points to config.json.
    """
    from sphere_aae.model import MODEL_PRESETS  # pylint: disable=import-outside-toplevel

    if isinstance(config, str) and config in MODEL_PRESETS:
        logger.info("%s preset model: %s", FOUND, config)
        content = MODEL_PRESETS[config].copy()
        content["model_preset_tag"] = config
        temp_file = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            suffix=".json",
            delete=False,
        )
        logger.info("Dumping config to: %s", temp_file.name)
        config_path = Path(temp_file.name)
        with config_path.open("w", encoding="utf-8") as config_file:
            json.dump(content, config_file, indent=2)
    else:
        config_path = Path(config)
    if not config_path.exists():
        raise ValueError(f"{config_path} does not exist.")

    if config_path.is_dir():
        # search config.json under config path
        config_json_path = config_path / "config.json"
        if not config_json_path.exists():
            raise ValueError(f"Fail to find config.json under {config_path}.")
    else:
        config_json_path = config_path

    logger.info("%s model configuration: %s", FOUND, config_json_path)
    return config_json_path


def detect_model_type(model_type: str, config: Path) -> "Model":
    """Detect the model type from the configuration file. If `model_type` is "auto", it will be
    inferred from the configuration file. Otherwise, it will be used as the model type, and sanity
    check will be performed.

    Parameters
    ----------
    model_type : str
        The model type, for example, "llama".

    config : pathlib.Path
        The path to config.json.

    Returns
    -------
    model : sphere_aae.compiler.Model
        The model type.
    """

    from sphere_aae.model import MODELS  # pylint: disable=import-outside-toplevel

    if model_type == "auto":
        with open(config, "r", encoding="utf-8") as config_file:
            cfg = json.load(config_file)
        if "model_type" not in cfg and (
            "model_config" not in cfg or "model_type" not in cfg["model_config"]
        ):
            raise ValueError(
                f"'model_type' not found in: {config}. "
                f"Please explicitly specify `--model-type` instead."
            )
        model_type = cfg["model_type"] if "model_type" in cfg else cfg["model_config"]["model_type"]
    if model_type in ["mixformer-sequential"]:
        model_type = "phi-msft"
    logger.info("%s model type: %s. Use `--model-type` to override.", FOUND, bold(model_type))
    if model_type not in MODELS:
        raise ValueError(f"Unknown model type: {model_type}. Available ones: {list(MODELS.keys())}")
    return MODELS[model_type]


def detect_quantization(quantization_arg: str, config: Path) -> "Quantization":
    """Detect the model quantization scheme from the configuration file or `--quantization`
    argument. If `--quantization` is provided, it will override the value on the configuration
    file.

    Parameters
    ----------
    quantization_arg : str
        The quantization scheme, for example, "q4f16_1".

    config : pathlib.Path
        The path to sphere-aae-chat-config.json.

    Returns
    -------
    quantization : sphere_aae.quantization.Quantization
        The model quantization scheme.
    """
    from sphere_aae.quantization import (  # pylint: disable=import-outside-toplevel
        QUANTIZATION,
    )

    with open(config, "r", encoding="utf-8") as config_file:
        cfg = json.load(config_file)
    if quantization_arg is not None:
        quantization = QUANTIZATION[quantization_arg]
    elif "quantization" in cfg:
        quantization = QUANTIZATION[cfg["quantization"]]
    else:
        raise ValueError(
            f"'quantization' not found in: {config}. "
            f"Please explicitly specify `--quantization` instead."
        )
    return quantization
