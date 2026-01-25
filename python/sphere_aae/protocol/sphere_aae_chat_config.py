# pylint: disable=too-many-instance-attributes
"""Schema for sphere-aae-chat-config"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from sphere_aae.support.constants import SPHERE_AAE_CHAT_CONFIG_VERSION

from .conversation_protocol import Conversation

SPHERE_AAE_CHAT_SYSTEM_DEFAULT = {
    "pad_token_id": 0,
    "bos_token_id": 1,
    "eos_token_id": 2,
    "temperature": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "repetition_penalty": 1.0,
    "top_p": 1.0,
}
"""system default values."""


class SphereAaeChatConfig(BaseModel):
    """Fields in the dumped `sphere-aae-chat-config.json` file."""

    # Version control
    version: str = SPHERE_AAE_CHAT_CONFIG_VERSION

    # use alias to avoid protected namespace conflict with pydantic
    field_model_type: str = Field(alias="model_type")
    quantization: str
    # use alias to avoid protected namespace conflict with pydantic
    field_model_config: Dict[str, Any] = Field(alias="model_config")
    vocab_size: int
    context_window_size: int
    sliding_window_size: int
    prefill_chunk_size: int
    attention_sink_size: int
    tensor_parallel_shards: int
    pipeline_parallel_stages: int = 1
    # Configuration of text generation
    active_vocab_size: int = None
    temperature: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    repetition_penalty: Optional[float] = None
    top_p: Optional[float] = None
    # Tokenizer configuration
    tokenizer_files: List[str] = Field(default_factory=list)
    # The content of tokenizer.TokenizerInfo
    tokenizer_info: Dict[str, Any] = Field(default_factory=dict)
    # conversation template
    conv_template: Conversation
    # extra fields from generation_config.json
    # NOTE: they are not being used for now in SphereAaeEngine
    # but we keep them for book-keep purposes
    pad_token_id: Optional[int] = None
    bos_token_id: Optional[int] = None
    eos_token_id: Optional[Union[int, List[int]]] = None

    def get_system_defaults_for_missing_fields(self) -> Dict[str, Any]:
        """Apply system default value for fields that are None

        Note
        ----
        We implement default setting in this way so we can lazily create
        SphereAaeChatConfig, override its optional values then
        apply_system_defaults in the end.
        """
        res = {}
        for key, value in SPHERE_AAE_CHAT_SYSTEM_DEFAULT.items():
            if getattr(self, key) is None:
                res[key] = value
        return res
