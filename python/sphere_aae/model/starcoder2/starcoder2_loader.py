"""
This file specifies how MLC's Starcoder2 parameter maps from other formats, for example HuggingFace
PyTorch, HuggingFace safetensors.
"""

import functools

import numpy as np

from sphere_aae.loader import ExternMapping
from sphere_aae.quantization import Quantization

from .starcoder2_model import Starcoder2Config, Starcoder2ForCausalLM


def huggingface(model_config: Starcoder2Config, quantization: Quantization) -> ExternMapping:
    """Returns a parameter mapping that maps from the names of Astro Agent Edge (AAE) parameters to
    the names of HuggingFace PyTorch parameters.

    Parameters
    ----------
    model_config : InternLMConfig
        The configuration of the InternLM model.

    quantization : Quantization
        The quantization configuration.

    Returns
    -------
    param_map : ExternMapping
        The parameter mapping from MLC to HuggingFace PyTorch.
    """
    model = Starcoder2ForCausalLM(model_config)
    if quantization is not None:
        model.to(quantization.model_dtype)
    _, _named_params, _ = model.export_tvm(  # type: ignore[misc]
        spec=model.get_default_spec(),
        allow_extern=True,
    )
    named_parameters = dict(_named_params)

    mapping = ExternMapping()

    sphere_aae_name = "lm_head.weight"
    sphere_aae_param = named_parameters[sphere_aae_name]
    mapping.add_mapping(
        sphere_aae_name,
        ["model.embed_tokens.weight"],
        functools.partial(
            lambda x, dtype: x.astype(dtype),
            dtype=sphere_aae_param.dtype,
        ),
    )

    for i in range(model_config.num_hidden_layers):
        # Add QKV in self attention
        attn = f"model.layers.{i}.self_attn"
        sphere_aae_name = f"{attn}.wqkv_pack.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                f"{attn}.q_proj.weight",
                f"{attn}.k_proj.weight",
                f"{attn}.v_proj.weight",
            ],
            functools.partial(
                lambda q, k, v, dtype: np.concatenate([q, k, v], axis=0).astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )
        sphere_aae_name = f"{attn}.wqkv_pack.bias"
        if sphere_aae_name in named_parameters:
            sphere_aae_param = named_parameters[sphere_aae_name]
            mapping.add_mapping(
                sphere_aae_name,
                [
                    f"{attn}.q_proj.bias",
                    f"{attn}.k_proj.bias",
                    f"{attn}.v_proj.bias",
                ],
                functools.partial(
                    lambda q, k, v, dtype: np.concatenate([q, k, v], axis=0).astype(dtype),
                    dtype=sphere_aae_param.dtype,
                ),
            )
        # Add gates in MLP

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
