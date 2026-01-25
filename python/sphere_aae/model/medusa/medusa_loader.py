"""
This file specifies how MLC's Medusa parameter maps from other formats, for example HuggingFace
PyTorch, HuggingFace safetensors.
"""

import functools

from sphere_aae.loader import ExternMapping
from sphere_aae.quantization import Quantization

from .medusa_model import MedusaConfig, MedusaModel


def huggingface(model_config: MedusaConfig, quantization: Quantization) -> ExternMapping:
    """Returns a parameter mapping that maps from the names of Astro Agent Edge (AAE) parameters to
    the names of HuggingFace PyTorch parameters.

    Parameters
    ----------
    model_config : MedusaConfig
        The configuration of the Medusa model.

    quantization : Quantization
        The quantization configuration.

    Returns
    -------
    param_map : ExternMapping
        The parameter mapping from MLC to HuggingFace PyTorch.
    """
    model = MedusaModel(model_config)
    if quantization is not None:
        model.to(quantization.model_dtype)
    _, _named_params, _ = model.export_tvm(  # type: ignore[misc]
        spec=model.get_default_spec(),
        allow_extern=True,
    )
    named_parameters = dict(_named_params)

    mapping = ExternMapping()

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
