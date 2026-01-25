# pylint: disable=W0611
"""
This file specifies how MLC's InternLM2 parameter maps from other formats, for example HuggingFace
PyTorch, HuggingFace safetensors.
"""

import functools

import numpy as np

from sphere_aae.loader import ExternMapping
from sphere_aae.quantization import Quantization

from .internlm2_model import InternLM2Config, InternLM2ForCausalLM


def huggingface(model_config: InternLM2ForCausalLM, quantization: Quantization) -> ExternMapping:
    """Returns a parameter mapping that maps from the names of Astro Agent Edge (AAE) parameters to
    the names of HuggingFace PyTorch parameters.

    Parameters
    ----------
    model_config : InternLM2Config
        The configuration of the InternLM2 model.

    quantization : Quantization
        The quantization configuration.

    Returns
    -------
    param_map : ExternMapping
        The parameter mapping from MLC to HuggingFace PyTorch.
    """
    model = InternLM2ForCausalLM(model_config)
    if quantization is not None:
        model.to(quantization.model_dtype)
    _, _named_params, _ = model.export_tvm(  # type: ignore[misc]
        spec=model.get_default_spec(),
        allow_extern=True,
    )
    named_parameters = dict(_named_params)

    mapping = ExternMapping()

    def _convert_wqkv_layout(wqkv, dtype):
        config = model_config
        kv_groups = config.num_attention_heads // config.num_key_value_heads
        head_dim = config.hidden_size // config.num_attention_heads
        wqkv = wqkv.reshape(-1, 2 + kv_groups, head_dim, wqkv.shape[-1])
        wq, wk, wv = np.split(wqkv, [kv_groups, kv_groups + 1], axis=1)  # pylint: disable=W0632
        wq = wq.reshape(-1, wq.shape[-1])
        wk = wk.reshape(-1, wk.shape[-1])
        wv = wv.reshape(-1, wv.shape[-1])
        return np.concatenate([wq, wk, wv], axis=0).astype(dtype)

    for i in range(model_config.num_hidden_layers):
        # Add gates in MLP
        mlp = f"model.layers.{i}.feed_forward"
        sphere_aae_name = f"{mlp}.gate_up_proj.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [
                f"{mlp}.w1.weight",
                f"{mlp}.w3.weight",
            ],
            functools.partial(
                lambda w1, w3, dtype: np.concatenate([w1, w3], axis=0).astype(dtype),
                dtype=sphere_aae_param.dtype,
            ),
        )

        sphere_aae_name = f"model.layers.{i}.attention.wqkv.weight"
        sphere_aae_param = named_parameters[sphere_aae_name]
        mapping.add_mapping(
            sphere_aae_name,
            [sphere_aae_name],
            functools.partial(
                _convert_wqkv_layout,
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
