"""
LangChain Chat Model Factory
Unified factory function for creating LangChain chat models
"""
import logging
from typing import Optional
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def create_chat_model(
    provider,
    model_name: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    **additional_params
) -> BaseChatModel:
    """
    Unified factory method for creating LangChain chat models
    
    Args:
        provider: ModelProvider instance, containing interface_type, api_key, api_base_url
        model_name: Model name
        temperature: Temperature parameter
        max_tokens: Max output tokens
        **additional_params: Other additional parameters
        
    Returns:
        BaseChatModel: LangChain chat model instance
        
    Raises:
        ValueError: Raised when creation fails
    """
    # Map interface type to provider name for init_chat_model
    interface_to_provider = {
        "OPENAI": "openai",
        "ANTHROPIC": "anthropic",
        "XAI": "xai",
        "GOOGLE": "google-genai",
        "OLLAMA": "openai",  # Reuse OpenAI client for Ollama
    }
    
    # Prepare model parameters
    model_params = {
        "temperature": temperature,
        "api_key": provider.api_key,
        **additional_params
    }
    
    # Add max_tokens if specified
    if max_tokens:
        model_params["max_tokens"] = max_tokens
    
    # Add base_url if available
    if provider.api_base_url:
        model_params["base_url"] = provider.api_base_url
    
    # Enable streaming usage for OpenAI-compatible providers
    interface_type = provider.interface_type.upper()
    logger.debug(f"Creating chat model for interface type: {interface_type}")
    
    if interface_type in ("OPENAI", "OLLAMA"):
        model_params["stream_usage"] = True
    
    # Get provider name - raise error if unsupported
    if interface_type not in interface_to_provider:
        raise ValueError(
            f"Unsupported interface_type: {interface_type}. "
            f"Supported types: {list(interface_to_provider.keys())}"
        )
    
    model_provider = interface_to_provider[interface_type]
    
    logger.info(f"Creating {model_provider} client for model: {model_name}")
    
    try:
        # Use init_chat_model for unified initialization
        return init_chat_model(
            model=model_name,
            model_provider=model_provider,
            **model_params
        )
    except Exception as e:
        error_msg = f"Failed to create chat model {model_name} with provider {model_provider}: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
