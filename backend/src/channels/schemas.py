from pydantic import BaseModel, Field, UUID4, HttpUrl
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ChannelProvider(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WECOM = "wecom"
    WECOM_SMART_BOT = "wecom_smart_bot"
    WECOM_WEBHOOK = "wecom_webhook"
    SLACK = "slack"

# --- Credentials Schemas ---
class TelegramCredentials(BaseModel):
    bot_token: str

class DiscordCredentials(BaseModel):
    bot_token: str
    application_id: Optional[str] = None
    public_key: Optional[str] = None

class WecomCredentials(BaseModel):
    corp_id: str
    agent_id: str
    secret: str
    token: str
    aes_key: str

# --- Base Schemas ---
class ChannelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: ChannelProvider
    is_active: bool = True
    settings: Dict[str, Any] = {}

class ChannelCreate(ChannelBase):
    assistant_id: Optional[UUID4] = None
    credentials: Dict[str, Any]  # Value structure depends on provider
    
class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    assistant_id: Optional[UUID4] = None

class ChannelRead(ChannelBase):
    id: UUID4
    owner_id: Optional[UUID4] = None
    assistant_id: Optional[UUID4] = None
    credentials: Dict[str, Any] # <--- Changed from implicit to explicit, although ChannelBase doesn't have it
    metadata: Dict[str, Any] = Field(alias="metadata_")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# --- Webhook Schemas ---
# Used for documenting incoming payloads if necessary, 
# but usually we handle raw requests in the adapter.
