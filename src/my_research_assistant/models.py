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
DEFAULT_EMBEDDING_MODEL = os.environ.get('DEFAULT_EMBEDDING_MODEL', 'text-embedding-ada-002')
MODEL_API_BASE = os.environ.get('MODEL_API_BASE', 'https://api.openai.com/v1')
MODEL_API_KEY = os.environ.get('OPENAI_API_KEY')

# Configure the global embedding model for LlamaIndex
# This model is used for all vector indexing and retrieval operations
Settings.embed_model = OpenAIEmbedding(
    model=DEFAULT_EMBEDDING_MODEL,
    api_base=MODEL_API_BASE,
    api_key=MODEL_API_KEY
)

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
        _CACHED_MODEL = OpenAI(model=DEFAULT_MODEL, api_base=MODEL_API_BASE,
                               api_key=MODEL_API_KEY, **model_kwargs)
        _CACHED_MODEL_KWARGS = model_kwargs
        return _CACHED_MODEL
    elif model_kwargs==_CACHED_MODEL_KWARGS:
        return _CACHED_MODEL
    else:
        return OpenAI(model=DEFAULT_MODEL, api_base=MODEL_API_BASE,
                      api_key=MODEL_API_KEY, **model_kwargs)

