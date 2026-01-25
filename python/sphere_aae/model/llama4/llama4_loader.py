"""
This file specifies how MLC's Llama parameter maps from other formats, for example HuggingFace
PyTorch, HuggingFace safetensors.
"""

import functools

import numpy as np

from sphere_aae.loader import ExternMapping
from sphere_aae.quantization import Quantization

from .llama4_model import Llama4Config, Llama4ForCausalLM


def huggingface(model_config: Llama4Config, quantization: Quantization) -> ExternMapping:
    """Returns a parameter mapping that maps from the names of Astro Agent Edge (AAE) parameters to
    the names of HuggingFace PyTorch parameters.

    Parameters
    ----------
    model_config : Llama4Config
        The configuration of the Llama model.

    quantization : Quantization
        The quantization configuration.

    Returns
    -------
    param_map : ExternMapping
        The parameter mapping from MLC to HuggingFace PyTorch.
    """
    model = Llama4ForCausalLM(model_config)
    if quantization is not None:
        model.to(quantization.model_dtype)
    _, _named_params, _ = model.export_tvm(  # type: ignore[misc]
        spec=model.get_default_spec(),
        allow_extern=True,
    )
    named_parameters = dict(_named_params)

    mapping = ExternMapping()

    for i in range(model_config.text_config.num_hidden_layers):
        # Add shared expert weights
        mlp = f"model.layers.{i}.feed_forward.shared_expert"
        sphere_aae_name = f"{mlp}.gate_up_proj.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                f"language_model.{mlp}.gate_proj.weight",
                f"language_model.{mlp}.up_proj.weight",
            ],
            functools.partial(
                lambda gate, up, dtype: np.concatenate([gate, up], axis=0).astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

        # Add router weights
        mlp = f"model.layers.{i}.feed_forward"
        sphere_aae_name = f"{mlp}.router.router.weight"
        hf_name = f"language_model.{mlp}.router.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                hf_name,
            ],
            functools.partial(
                lambda x, dtype: x.astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

        # Add experts weights
        mlp = f"model.layers.{i}.feed_forward"
        hf_name = f"language_model.{mlp}.experts.gate_up_proj"
        sphere_aae_name = f"{mlp}.experts.gate_up_proj"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                hf_name,
            ],
            functools.partial(
                lambda x, dtype: x.astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

        mlp = f"model.layers.{i}.feed_forward"
        sphere_aae_name = f"{mlp}.experts.down_proj"
        hf_name = f"language_model.{mlp}.experts.down_proj"

        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                hf_name,
            ],
            functools.partial(
                lambda x, dtype: x.astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

    for sphere_aae_name, sphere_aae_param in named_parameters.items():
        if sphere_aae_name not in mapping.param_map:
            mapping.add_mapping(
                sphere_aae_name,
                [f"language_model.{sphere_aae_name}"],
                functools.partial(
                    lambda x, dtype: x.astype(dtype),
                    dtype=sphere_aae_param.dtype,
                ),
            )
    return mapping
