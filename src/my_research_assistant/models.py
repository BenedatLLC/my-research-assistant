"""
Maintain configuration for models.
"""
import os
from typing import Optional
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import LLM

DEFAULT_MODEL_NAME = os.environ.get('DEFAULT_MODEL', 'gpt-4o')

_CACHED_MODEL:Optional[LLM] = None
_CACHED_MODEL_KWARGS = None

def get_default_model(**model_kwargs) -> LLM:
    """Instantiate an instance of the default model. Will cache the first model
    requested. If you call again with the same keyword args, you will get the same model.
    Otherwise, it will instantiate a model specific to your request.
    """
    global _CACHED_MODEL
    global _CACHED_MODEL_KWARGS
    if _CACHED_MODEL is None:
        _CACHED_MODEL = OpenAI(model=DEFAULT_MODEL_NAME, **model_kwargs)
        _CACHED_MODEL_KWARGS = model_kwargs
        return _CACHED_MODEL
    elif model_kwargs==_CACHED_MODEL_KWARGS:
        return _CACHED_MODEL
    else:
        return OpenAI(model=DEFAULT_MODEL_NAME, **model_kwargs)

