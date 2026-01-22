"""
Configuration module for LLM provider selection and API key management.
"""

import os
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    APIFREELLM = "apifreellm"


def get_llm_provider() -> LLMProvider:
    """
    Get the configured LLM provider from environment variable.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    try:
        return LLMProvider(provider)
    except ValueError:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider}. Must be 'openai' or 'apifreellm'"
        )


def get_api_key() -> str:
    """
    Get the API key for the configured LLM provider.
    """
    provider = get_llm_provider()
    
    if provider == LLMProvider.OPENAI:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        return key
    
    elif provider == LLMProvider.APIFREELLM:
        key = os.getenv("APIFREELLM_API_KEY")
        if not key:
            raise ValueError("APIFREELLM_API_KEY environment variable not set")
        return key


def get_model_name() -> str:
    """
    Get the model name for the configured provider.
    """
    provider = get_llm_provider()
    
    if provider == LLMProvider.OPENAI:
        return os.getenv("LLM_MODEL", "gpt-4o-mini")
    elif provider == LLMProvider.APIFREELLM:
        return os.getenv("LLM_MODEL", "gpt-4-turbo")


def get_base_url() -> str | None:
    """
    Get the base URL for the LLM API (if needed).
    """
    provider = get_llm_provider()
    
    if provider == LLMProvider.APIFREELLM:
        return os.getenv("LLM_BASE_URL", "https://api.apifreellm.com/v1")
    
    return None
