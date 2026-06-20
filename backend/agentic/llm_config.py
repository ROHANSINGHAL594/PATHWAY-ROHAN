"""
LLM Configuration Module

This module centralizes all LLM provider configurations, API keys, and model settings.
It provides a single source of truth for LLM-related configuration across the agentic service.

Supported Providers:
- Groq: Fast inference, good for agent operations
- OpenAI: GPT models including o1 reasoning model
- Anthropic: Claude models for complex reasoning
- Gemini: Google's models, used as fallback provider

Environment Variables Required:
- GROQ_API_KEY: API key for Groq
- OPENAI_API_KEY: API key for OpenAI
- ANTHROPIC_API_KEY: API key for Anthropic Claude
- GEMINI_API_KEY: API key for Google Gemini
- DEFAULT_AGENT_PROVIDER: Provider to use for agent operations (default: groq)
- DEFAULT_REASONING_PROVIDER: Provider to use for reasoning tasks (default: openai)
- DEFAULT_ALERT_PROVIDER: Provider to use for alert generation (default: groq)
- DEFAULT_SQL_PROVIDER: Provider to use for SQL operations (default: groq)
"""

import os
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class LLMUseCase(str, Enum):
    """Enumeration of different LLM use cases."""
    AGENT = "agent"
    REASONING = "reasoning"
    ALERT = "alert"
    SQL = "sql"
    SUMMARIZATION = "summarization"
    ANALYSER = "analyser"  # For RCA (Root Cause Analysis) tasks


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_name: str
    temperature: float
    max_retries: int
    additional_params: Dict[str, Any]


# Model name mappings per provider
# To add new models or change defaults, update these dictionaries
MODEL_NAMES = {
    LLMProvider.GROQ: {
        "default": "llama-3.3-70b-versatile",
        "alternatives": [
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
    },
    LLMProvider.OPENAI: {
        "default": "gpt-4o",
        "reasoning": "o1",
        "summarization": "o1",
        "alternatives": [
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ]
    },
    LLMProvider.ANTHROPIC: {
        "default": "claude-3-5-sonnet-20241022",
        "alternatives": [
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229"
        ]
    },
    LLMProvider.GEMINI: {
        "default": "gemini-2.5-flash",
        "fallback": "gemini-2.5-flash",
        "alternatives": [
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]
    }
}


# Preset configurations for different use cases
# These can be overridden at runtime by passing parameters to get_model()
USE_CASE_PRESETS = {
    LLMUseCase.AGENT: ModelConfig(
        model_name="default",
        temperature=0.0,
        max_retries=2,
        additional_params={}
    ),
    LLMUseCase.REASONING: ModelConfig(
        model_name="default",
        temperature=1.0,
        max_retries=3,
        additional_params={}
    ),
    LLMUseCase.ALERT: ModelConfig(
        model_name="default",
        temperature=0.2,
        max_retries=2,
        additional_params={}
    ),
    LLMUseCase.SQL: ModelConfig(
        model_name="default",
        temperature=0.0,
        max_retries=3,
        additional_params={}
    ),
    LLMUseCase.SUMMARIZATION: ModelConfig(
        model_name="default",
        temperature=1.0,
        max_retries=3,
        additional_params={}
    ),
    LLMUseCase.ANALYSER: ModelConfig(
        model_name="default",
        temperature=0.3,  # Balanced - some creativity but mostly deterministic
        max_retries=3,
        additional_params={}
    ),
}


# Default provider selection per use case
# Can be overridden via environment variables
DEFAULT_PROVIDERS = {
    LLMUseCase.AGENT: LLMProvider.GROQ,
    LLMUseCase.REASONING: LLMProvider.OPENAI,
    LLMUseCase.ALERT: LLMProvider.GROQ,
    LLMUseCase.SQL: LLMProvider.GROQ,
    LLMUseCase.SUMMARIZATION: LLMProvider.OPENAI,
    LLMUseCase.ANALYSER: LLMProvider.GEMINI,  # Use Gemini for RCA analysis
}


# Fallback provider when primary provider fails or API key is missing
FALLBACK_PROVIDER = LLMProvider.GEMINI


def get_api_key(provider: LLMProvider) -> Optional[str]:
    """
    Retrieve API key for a given provider from environment variables.
    Validates that the key is not a placeholder value.
    
    Args:
        provider: The LLM provider
        
    Returns:
        API key string or None if not found or is a placeholder
    """
    key_mapping = {
        LLMProvider.GROQ: "GROQ_API_KEY",
        LLMProvider.OPENAI: "OPENAI_API_KEY",
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.GEMINI: "GOOGLE_API_KEY"
    }
    
    env_var = key_mapping.get(provider)
    if not env_var:
        return None
    
    api_key = os.getenv(env_var)
    
    # For Gemini, also check GEMINI_API_KEY as fallback
    if not api_key and provider == LLMProvider.GEMINI:
        api_key = os.getenv("GEMINI_API_KEY")
    
    # Check if key exists and is not a placeholder
    if not api_key:
        return None
    
    # Common placeholder patterns
    placeholder_patterns = [
        "your_",
        "sk-proj-",  # Invalid OpenAI format
        "placeholder",
        "example",
        "xxx",
        "..."
    ]
    
    # Check if it's too short or looks like a placeholder
    if len(api_key) < 10 or any(pattern in api_key.lower() for pattern in placeholder_patterns):
        return None
        
    return api_key


def get_default_provider(use_case: LLMUseCase) -> LLMProvider:
    """
    Get the default provider for a specific use case.
    Can be overridden by environment variables.
    
    Args:
        use_case: The use case for which to get the provider
        
    Returns:
        LLMProvider enum value
    """
    env_var_mapping = {
        LLMUseCase.AGENT: "DEFAULT_AGENT_PROVIDER",
        LLMUseCase.REASONING: "DEFAULT_REASONING_PROVIDER",
        LLMUseCase.ALERT: "DEFAULT_ALERT_PROVIDER",
        LLMUseCase.SQL: "DEFAULT_SQL_PROVIDER",
        LLMUseCase.SUMMARIZATION: "DEFAULT_SUMMARIZATION_PROVIDER"
    }
    
    env_var = env_var_mapping.get(use_case)
    if env_var:
        provider_str = os.getenv(env_var)
        if provider_str:
            try:
                return LLMProvider(provider_str.lower())
            except ValueError:
                pass
    
    return DEFAULT_PROVIDERS.get(use_case, LLMProvider.GROQ)


def get_model_name(provider: LLMProvider, use_case: LLMUseCase) -> str:
    """
    Get the appropriate model name for a provider and use case.
    
    Args:
        provider: The LLM provider
        use_case: The use case
        
    Returns:
        Model name string
    """
    provider_models = MODEL_NAMES.get(provider, {})
    
    # Special case for OpenAI reasoning model
    if provider == LLMProvider.OPENAI and use_case == LLMUseCase.REASONING:
        return provider_models.get("reasoning", provider_models.get("default", "gpt-4o"))
    
    # Special case for Gemini fallback
    if provider == LLMProvider.GEMINI:
        return provider_models.get("fallback", provider_models.get("default", "gemini-2.0-flash"))
    
    return provider_models.get("default", "")


def get_preset_config(use_case: LLMUseCase) -> ModelConfig:
    """
    Get the preset configuration for a specific use case.
    
    Args:
        use_case: The use case
        
    Returns:
        ModelConfig with preset values
    """
    return USE_CASE_PRESETS.get(use_case, USE_CASE_PRESETS[LLMUseCase.AGENT])


def validate_configuration() -> Dict[str, bool]:
    """
    Validate that all required API keys are present.
    
    Returns:
        Dictionary mapping provider names to boolean indicating if API key exists
    """
    return {
        provider.value: get_api_key(provider) is not None
        for provider in LLMProvider
    }
