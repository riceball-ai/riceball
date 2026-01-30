from typing import Any, Dict, Optional
from src.assistants.models import Assistant
from src.chat.providers.google_adapter import GoogleProviderAdapter

def resolve_assistant_model_params(assistant: Assistant) -> Dict[str, Any]:
    """
    Resolve and merge model parameters for an assistant from various sources:
    1. Model's base generation_config
    2. Assistant's legacy config.additional_params
    3. Assistant's model_parameters
    
    Also handles provider-specific normalization (e.g. Google).
    """
    
    def _merge_params(*param_dicts) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for params in param_dicts:
            if not params:
                continue
            for key, value in params.items():
                if value is None:
                    continue
                merged[key] = value
        return merged

    # 1. Base config from Model (if available)
    # Handle cases where assistant.model might fail to load or be incomplete
    model_generation_config = getattr(assistant.model, "generation_config", None) if assistant.model else None
    
    # 2. Legacy overrides from Assistant.config
    assistant_overrides = (assistant.config or {}).get("additional_params", {})
    
    # 3. New structured model_parameters
    new_params = assistant.model_parameters or {}

    # Merge in order of precedence (later overrides earlier)
    generation_params = _merge_params(model_generation_config, assistant_overrides, new_params)
    
    # 4. Remove keys that conflict with create_chat_model explicit args
    # to avoid "multiple values for argument" TypeError
    # (temperature, max_tokens are usually passed explicitly by callers)
    reserved_keys = ["temperature", "model_name", "provider"] 
    # max_tokens is sometimes passed explicitly, sometimes not. 
    # Safe to keep if caller expects it in **kwargs, but dangerous if caller passes it as arg.
    # We will let caller handle max_tokens extraction if they want to pass it explicitly.
    
    for key in reserved_keys:
        if key in generation_params:
            generation_params.pop(key)
    
    # 5. Provider-specific normalization (e.g., Google)
    adapter = GoogleProviderAdapter()
    if adapter.is_google_provider(assistant):
        generation_params = adapter.normalize_generation_params(generation_params, assistant)
        
    return generation_params
