import uuid
from typing import Any, Optional, Dict
from pydantic import BaseModel, Field


class ConfigCreate(BaseModel):
    """Request model for creating configuration items"""
    key: str = Field(..., min_length=1, max_length=255, description="Configuration key name")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    is_public: bool = Field(False, description="Whether this is a public configuration")
    is_enabled: bool = Field(True, description="Whether this configuration item is enabled")
    config_type: str = Field("text", description="UI component type")
    config_group: str = Field("general", description="Configuration group")
    label: Optional[str] = Field(None, description="Display label")
    options: Optional[str] = Field(None, description="Options for select type (JSON)")


class ConfigUpdate(BaseModel):
    """Request model for updating configuration items"""
    value: Optional[Any] = Field(None, description="Configuration value")
    description: Optional[str] = Field(None, description="Configuration description")
    is_public: Optional[bool] = Field(None, description="Whether this is a public configuration")
    is_enabled: Optional[bool] = Field(None, description="Whether this configuration item is enabled")
    config_type: Optional[str] = Field(None, description="UI component type")
    config_group: Optional[str] = Field(None, description="Configuration group")
    label: Optional[str] = Field(None, description="Display label")
    options: Optional[str] = Field(None, description="Options for select type (JSON)")


class ConfigResponse(BaseModel):
    """Configuration item response model"""
    id: uuid.UUID
    key: str
    value: Any
    description: Optional[str]
    is_public: bool
    is_enabled: bool
    config_type: str
    config_group: str
    label: Optional[str]
    options: Optional[str]
    created_at: Any
    updated_at: Any
    
    class Config:
        from_attributes = True


class PublicConfigResponse(BaseModel):
    """Public configuration response model"""
    key: str
    value: Any
    
    class Config:
        from_attributes = True


class ConfigListResponse(BaseModel):
    """Configuration list response model"""
    configs: list[ConfigResponse]
    total: int


class PublicConfigsResponse(BaseModel):
    """Public configurations collection response model"""
    configs: Dict[str, Any] = Field(..., description="Configuration key-value pairs")


class ConfigBatchUpdate(BaseModel):
    """Request model for batch updating configurations"""
    configs: Dict[str, Any] = Field(..., description="Configuration key-value pairs to update")