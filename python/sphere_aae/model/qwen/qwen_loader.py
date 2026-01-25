"""
This file specifies how MLC's QWen parameter maps from other formats, for example HuggingFace
PyTorch, HuggingFace safetensors.
"""

import functools

import numpy as np

from sphere_aae.loader import ExternMapping
from sphere_aae.quantization import Quantization

from .qwen_model import QWenConfig, QWenLMHeadModel


def huggingface(model_config: QWenConfig, quantization: Quantization) -> ExternMapping:
    """Returns a parameter mapping that maps from the names of Astro Agent Edge (AAE) parameters to
    the names of HuggingFace PyTorch parameters.

    Parameters
    ----------
    model_config : QWenConfig
        The configuration of the Qwen model.

    quantization : Quantization
        The quantization configuration.

    Returns
    -------
    param_map : ExternMapping
        The parameter mapping from MLC to HuggingFace PyTorch.
    """
    model = QWenLMHeadModel(model_config)
    if quantization is not None:
        model.to(quantization.model_dtype)
    _, _named_params, _ = model.export_tvm(  # type: ignore[misc]
        spec=model.get_default_spec(),
        allow_extern=True,
    )
    named_parameters = dict(_named_params)

    mapping = ExternMapping()

    for i in range(model_config.num_hidden_layers):
        # Add gates in MLP
        mlp = f"transformer.h.{i}.mlp"
        sphere_aae_name = f"{mlp}.gate_up_proj.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                f"{mlp}.w1.weight",
                f"{mlp}.w2.weight",
            ],
            functools.partial(
                lambda gate, up, dtype: np.concatenate([gate, up], axis=0).astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

    for sphere_aae_name, sphere_aae_param in named_parameters.items():
        if sphere_aae_name not in mapping.param_map:
            mapping.add_mapping(
                sphere_aae_name,
                [sphere_aae_name],
                functools.partial(
                    lambda x, dtype: x.astype(dtype),
                    dtype=sphere_aae_param.dtype,
                ),
            )
    return mapping
