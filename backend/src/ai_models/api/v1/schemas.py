import uuid
from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from src.ai_models.models import ProviderStatusEnum, ModelStatusEnum, PROVIDER_INTERFACE_TYPES

# Allowed model capabilities range
ALLOWED_MODEL_CAPABILITIES = [
    "chat",
    "completion",
    "embedding",
    "vision",
    "audio",
    "function_calling",
    "tool_use",
    "code",
    "image_generation",
    # Extend as needed
]


# Provider Schemas
class ModelProviderBase(BaseModel):
    name: str = Field(..., max_length=100, description="Provider name")
    display_name: str = Field(..., max_length=200, description="Provider display name")
    description: Optional[str] = Field(None, description="Provider description")
    website: Optional[str] = Field(None, max_length=500, description="Provider website")
    api_base_url: str = Field(..., max_length=500, description="API base URL")
    interface_type: str = Field(PROVIDER_INTERFACE_TYPES["CUSTOM"], description="Interface type")
    api_key: Optional[str] = Field(None, max_length=500, description="API key")
    status: ProviderStatusEnum = Field(ProviderStatusEnum.ACTIVE, description="Provider status")

    @field_validator("interface_type")
    @classmethod
    def validate_interface_type(cls, v):
        if v not in PROVIDER_INTERFACE_TYPES.values():
            allowed_types = list(PROVIDER_INTERFACE_TYPES.values())
            raise ValueError(f"interface_type must be one of: {allowed_types}")
        return v


class ModelProviderCreate(ModelProviderBase):
    pass


class ModelProviderUpdate(ModelProviderBase):
    pass


class ModelProviderResponse(ModelProviderBase):
    id: uuid.UUID = Field(..., description="Provider ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# Model Schemas

class ModelBase(BaseModel):
    name: str = Field(..., max_length=200, description="Model name")
    display_name: str = Field(..., max_length=300, description="Model display name")
    description: Optional[str] = Field(None, description="Model description")
    capabilities: List[str] = Field(default=[], description="Model capabilities")
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific generation parameters (modalities, tools, image config, etc.)")
    status: ModelStatusEnum = Field(ModelStatusEnum.ACTIVE, description="Model status")
    max_context_tokens: Optional[int] = Field(None, description="Maximum context tokens")
    max_output_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    provider_id: uuid.UUID = Field(..., description="Provider ID")

    @field_validator("capabilities", mode="before")
    @classmethod
    def validate_capabilities(cls, v):
        if v is None:
            return []
        invalid = [c for c in v if c not in ALLOWED_MODEL_CAPABILITIES]
        if invalid:
            raise ValueError(f"capabilities contains invalid values: {invalid}, allowed range: {ALLOWED_MODEL_CAPABILITIES}")
        return v


class ModelCreate(ModelBase):
    pass



class ModelUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200, description="Model name")
    display_name: Optional[str] = Field(None, max_length=300, description="Model display name")
    description: Optional[str] = Field(None, description="Model description")
    capabilities: Optional[List[str]] = Field(None, description="Model capabilities")
    generation_config: Optional[Dict[str, Any]] = Field(None, description="Provider-specific generation parameters")
    status: Optional[ModelStatusEnum] = Field(None, description="Model status")
    max_context_tokens: Optional[int] = Field(None, description="Maximum context tokens")
    max_output_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    provider_id: Optional[uuid.UUID] = Field(None, description="Provider ID")

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v):
        if v is None:
            return v
        invalid = [c for c in v if c not in ALLOWED_MODEL_CAPABILITIES]
        if invalid:
            raise ValueError(f"capabilities contains invalid values: {invalid}, allowed range: {ALLOWED_MODEL_CAPABILITIES}")
        return v


class ModelResponse(ModelBase):
    id: uuid.UUID = Field(..., description="Model ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    provider: Optional[ModelProviderResponse] = Field(None, description="Associated provider")

    class Config:
        from_attributes = True
