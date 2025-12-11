"""
Maintain configuration for models.
"""
import os
from typing import Optional
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding

DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'gpt-4o')
DEFAULT_REASONING_MODEL = os.environ.get('DEFAULT_REASONING_MODEL', 'gpt-5.1')
DEFAULT_EMBEDDING_MODEL = os.environ.get('DEFAULT_EMBEDDING_MODEL', 'text-embedding-ada-002')
MODEL_API_BASE = os.environ.get('MODEL_API_BASE', 'https://api.openai.com/v1')
MODEL_API_KEY = os.environ.get('OPENAI_API_KEY')
assert MODEL_API_KEY is not None and MODEL_API_KEY!="", "Need to set environment variable OPENAI_API_KEY"

# Configure the global embedding model for LlamaIndex
# This model is used for all vector indexing and retrieval operations
Settings.embed_model = OpenAIEmbedding(
    model=DEFAULT_EMBEDDING_MODEL,
    api_base=MODEL_API_BASE,
    api_key=MODEL_API_KEY
)

_CACHED_MODEL:Optional[LLM] = None
_CACHED_MODEL_KWARGS = None

_CACHED_REASONING_MODEL:Optional[LLM] = None
_CACHED_REASONING_MODEL_KWARGS = None

def get_default_model(**model_kwargs) -> LLM:
    """Instantiate an instance of the default model. Will cache the first model
    requested. If you call again with the same keyword args, you will get the same model.
    Otherwise, it will instantiate a model specific to your request.
    """
    global _CACHED_MODEL
    global _CACHED_MODEL_KWARGS
    if _CACHED_MODEL is None:
        _CACHED_MODEL = OpenAI(model=DEFAULT_MODEL, api_base=MODEL_API_BASE,
                               api_key=MODEL_API_KEY, **model_kwargs)
        _CACHED_MODEL_KWARGS = model_kwargs
        return _CACHED_MODEL
    elif model_kwargs==_CACHED_MODEL_KWARGS:
        return _CACHED_MODEL
    else:
        return OpenAI(model=DEFAULT_MODEL, api_base=MODEL_API_BASE,
                      api_key=MODEL_API_KEY, **model_kwargs)

def get_reasoning_model(**model_kwargs) -> LLM:
    """Instantiate an instance of the reasoning model. Will cache the first model
    requested. If you call again with the same keyword args, you will get the same model.
    Otherwise, it will instantiate a model specific to your request.

    The reasoning model is intended for tasks that require deeper analytical thinking,
    such as complex research synthesis, multi-step reasoning, or detailed analysis.

    The model is configured with reasoning_effort="high" by default for maximum
    analytical capability. This can be overridden by passing a different value
    in model_kwargs.
    """
    global _CACHED_REASONING_MODEL
    global _CACHED_REASONING_MODEL_KWARGS

    # Set reasoning_effort to "high" by default, but allow override
    if 'reasoning_effort' not in model_kwargs:
        model_kwargs = {**model_kwargs, 'reasoning_effort': 'high'}

    if _CACHED_REASONING_MODEL is None:
        _CACHED_REASONING_MODEL = OpenAI(model=DEFAULT_REASONING_MODEL, api_base=MODEL_API_BASE,
                                         api_key=MODEL_API_KEY, **model_kwargs)
        _CACHED_REASONING_MODEL_KWARGS = model_kwargs
        return _CACHED_REASONING_MODEL
    elif model_kwargs==_CACHED_REASONING_MODEL_KWARGS:
        return _CACHED_REASONING_MODEL
    else:
        return OpenAI(model=DEFAULT_REASONING_MODEL, api_base=MODEL_API_BASE,
                      api_key=MODEL_API_KEY, **model_kwargs)
