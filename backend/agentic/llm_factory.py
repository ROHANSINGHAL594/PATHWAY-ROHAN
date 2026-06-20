"""
LLM Factory Module

This module provides factory functions for creating LLM instances across different providers.
It handles provider selection, fallback logic, and configuration management.

Usage:
    from llm_factory import get_model, create_agent_model, create_reasoning_model
    
    # Get a model for a specific use case (automatic provider selection)
    model = create_agent_model()
    
    # Get a model with explicit provider
    model = get_model(LLMUseCase.REASONING, provider=LLMProvider.ANTHROPIC)
    
    # Override parameters
    model = create_reasoning_model(temperature=0.5, max_retries=5)
"""

import os
from typing import Optional, Any
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

# Try relative import first (when used as package), fallback to direct import
try:
    from .llm_config import (
        LLMProvider,
        LLMUseCase,
        get_api_key,
        get_default_provider,
        get_model_name,
        get_preset_config,
        FALLBACK_PROVIDER
    )
except ImportError:
    from llm_config import (
        LLMProvider,
        LLMUseCase,
        get_api_key,
        get_default_provider,
        get_model_name,
        get_preset_config,
        FALLBACK_PROVIDER
    )


def _create_groq_model(
    model_name: str,
    temperature: float,
    max_retries: int,
    api_key: str,
    **kwargs
) -> ChatGroq:
    """
    Create a Groq model instance.
    
    Args:
        model_name: Name of the Groq model
        temperature: Temperature setting
        max_retries: Maximum number of retries
        api_key: Groq API key
        **kwargs: Additional parameters to pass to ChatGroq
        
    Returns:
        ChatGroq instance
    """
    return ChatGroq(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
        **kwargs
    )


def _create_openai_model(
    model_name: str,
    temperature: float,
    max_retries: int,
    api_key: str,
    **kwargs
) -> ChatOpenAI:
    """
    Create an OpenAI model instance.
    
    Args:
        model_name: Name of the OpenAI model
        temperature: Temperature setting
        max_retries: Maximum number of retries
        api_key: OpenAI API key
        **kwargs: Additional parameters to pass to ChatOpenAI
        
    Returns:
        ChatOpenAI instance
    """
    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
        **kwargs
    )


def _create_anthropic_model(
    model_name: str,
    temperature: float,
    max_retries: int,
    api_key: str,
    **kwargs
) -> ChatAnthropic:
    """
    Create an Anthropic Claude model instance.
    
    Args:
        model_name: Name of the Claude model
        temperature: Temperature setting
        max_retries: Maximum number of retries
        api_key: Anthropic API key
        **kwargs: Additional parameters to pass to ChatAnthropic
        
    Returns:
        ChatAnthropic instance
    """
    return ChatAnthropic(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        api_key=api_key,
        **kwargs
    )


def _create_gemini_model(
    model_name: str,
    temperature: float,
    max_retries: int,
    api_key: str,
    **kwargs
) -> ChatGoogleGenerativeAI:
    """
    Create a Google Gemini model instance.
    
    Args:
        model_name: Name of the Gemini model
        temperature: Temperature setting
        max_retries: Maximum number of retries
        api_key: Google API key
        **kwargs: Additional parameters to pass to ChatGoogleGenerativeAI
        
    Returns:
        ChatGoogleGenerativeAI instance
    """
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_retries=max_retries,
        google_api_key=api_key,
        **kwargs
    )


def get_model(
    use_case: LLMUseCase,
    provider: Optional[LLMProvider] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None,
    **kwargs
) -> BaseChatModel:
    """
    Get an LLM model instance for a specific use case.
    
    This is the main entry point for creating LLM models. It handles:
    - Automatic provider selection based on use case
    - Fallback to Gemini if primary provider's API key is missing
    - Preset configuration application
    - Parameter overrides
    
    Args:
        use_case: The use case for the model (AGENT, REASONING, etc.)
        provider: Optional explicit provider selection
        model_name: Optional model name override
        temperature: Optional temperature override
        max_retries: Optional max_retries override
        **kwargs: Additional provider-specific parameters
        
    Returns:
        BaseChatModel instance (ChatGroq, ChatOpenAI, etc.)
        
    Raises:
        ValueError: If no API keys are available (including fallback)
    """
    # Determine which provider to use
    selected_provider = provider if provider else get_default_provider(use_case)
    
    # Check if API key is available, fallback to Gemini if not
    api_key = get_api_key(selected_provider)
    if not api_key:
        print(f"Warning: {selected_provider.value} API key not found, falling back to {FALLBACK_PROVIDER.value}")
        selected_provider = FALLBACK_PROVIDER
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        # print("===========",api_key,'======================')
        
        if not api_key:
            raise ValueError(
                f"No API key found for {selected_provider.value}. "
                f"Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
            )
    
    # Get preset configuration for the use case
    preset = get_preset_config(use_case)
    
    # Determine final parameters (preset values can be overridden)
    final_model_name = model_name if model_name else get_model_name(selected_provider, use_case)
    final_temperature = temperature if temperature is not None else preset.temperature
    final_max_retries = max_retries if max_retries is not None else preset.max_retries
    
    # Merge additional params
    final_kwargs = {**preset.additional_params, **kwargs}
    
    # Create the appropriate model instance
    model_creators = {
        LLMProvider.GROQ: _create_groq_model,
        LLMProvider.OPENAI: _create_openai_model,
        LLMProvider.ANTHROPIC: _create_anthropic_model,
        LLMProvider.GEMINI: _create_gemini_model
    }
    
    creator = model_creators.get(selected_provider)
    if not creator:
        raise ValueError(f"Unsupported provider: {selected_provider}")
    
    return creator(
        model_name=final_model_name,
        temperature=final_temperature,
        max_retries=final_max_retries,
        api_key=api_key,
        **final_kwargs
    )


# Convenience functions for specific use cases

def create_agent_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for agent operations.
    
    Default configuration:
    - Provider: Groq (fast inference)
    - Temperature: 0.0 (deterministic)
    - Max retries: 2
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.AGENT, provider=provider, **kwargs)


def create_reasoning_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for complex reasoning tasks.
    
    Default configuration:
    - Provider: OpenAI (o1 model for reasoning)
    - Temperature: 1.0 (creative)
    - Max retries: 3
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.REASONING, provider=provider, **kwargs)


def create_alert_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for alert generation.
    
    Default configuration:
    - Provider: Groq (fast inference)
    - Temperature: 0.2 (slightly creative)
    - Max retries: 2
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.ALERT, provider=provider, **kwargs)


def create_sql_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for SQL query generation.
    
    Default configuration:
    - Provider: Groq (fast inference)
    - Temperature: 0.0 (deterministic)
    - Max retries: 3
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.SQL, provider=provider, **kwargs)


def create_summarization_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for summarization tasks.
    
    Default configuration:
    - Provider: OpenAI (good for text generation)
    - Temperature: 1.0 (creative)
    - Max retries: 3
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.SUMMARIZATION, provider=provider, **kwargs)


def create_analyser_model(
    provider: Optional[LLMProvider] = None,
    **kwargs
) -> BaseChatModel:
    """
    Create a model optimized for RCA (Root Cause Analysis) tasks.
    
    Default configuration:
    - Provider: Gemini (gemini-2.0-flash-exp for fast analysis)
    - Temperature: 0.3 (balanced - some creativity but mostly deterministic)
    - Max retries: 3
    
    Args:
        provider: Optional provider override
        **kwargs: Additional parameters or overrides
        
    Returns:
        BaseChatModel instance
    """
    return get_model(LLMUseCase.ANALYSER, provider=provider, **kwargs)
