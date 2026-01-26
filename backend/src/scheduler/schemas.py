from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional
from datetime import datetime

class ScheduledTaskBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    cron_expression: str = Field(..., json_schema_extra={"example": "0 9 * * *"})
    assistant_id: UUID4
    prompt_template: str
    channel_config_id: UUID4
    target_identifier: str = Field(..., min_length=0)
    is_active: bool = True

class ScheduledTaskCreate(ScheduledTaskBase):
    pass

class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    assistant_id: Optional[UUID4] = None
    prompt_template: Optional[str] = None
    channel_config_id: Optional[UUID4] = None
    target_identifier: Optional[str] = None
    is_active: Optional[bool] = None

class ScheduledTaskRead(ScheduledTaskBase):
    id: UUID4
    owner_id: UUID4
    last_run_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
