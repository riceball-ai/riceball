import enum
import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, JSON, Enum as SQLEnum, Numeric
from sqlalchemy.ext.mutable import MutableDict

from src.models import Base  # SQLAlchemy declarative Base

if TYPE_CHECKING:
    from src.assistants.models import Assistant


class ProviderStatusEnum(enum.Enum):
    """Provider status enumeration"""
    ACTIVE = "ACTIVE"  # Active and available
    INACTIVE = "INACTIVE"  # Disabled
    MAINTENANCE = "MAINTENANCE"  # Under maintenance


# Interface type constants - Use string constants instead of enum
PROVIDER_INTERFACE_TYPES = {
    "OPENAI": "OPENAI",      # OpenAI compatible interface
    "ANTHROPIC": "ANTHROPIC", # Anthropic interface
    "XAI": "XAI",        # xAI interface
    "GOOGLE": "GOOGLE",      # Google interface
    "DASHSCOPE": "DASHSCOPE", # Alibaba DashScope interface
    "CUSTOM": "CUSTOM",      # Custom interface (requires specific adapter)
}


class ModelStatusEnum(enum.Enum):
    """Model status enumeration"""
    ACTIVE = "ACTIVE"  # Active and available
    INACTIVE = "INACTIVE"  # Disabled
    UNAVAILABLE = "UNAVAILABLE"  # Temporarily unavailable (e.g., under maintenance)
    DEPRECATED = "DEPRECATED"  # Deprecated


class ModelProvider(Base):
    """Model provider table"""
    __tablename__ = "model_providers"

    # Provider name, e.g. OpenAI, Anthropic, Google, etc.
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    
    # Provider display name
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Provider description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Provider website
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # API base URL
    api_base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # API Key
    api_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Interface type - determines which adapter to use
    interface_type: Mapped[str] = mapped_column(
        String(50),
        default=PROVIDER_INTERFACE_TYPES["CUSTOM"],
        nullable=False
    )
    
    # Provider status
    status: Mapped[ProviderStatusEnum] = mapped_column(
        SQLEnum(ProviderStatusEnum), 
        default=ProviderStatusEnum.ACTIVE, 
        nullable=False
    )
    
    # Associated models
    models: Mapped[List["Model"]] = relationship(
        "Model", 
        back_populates="provider",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return self.display_name


class Model(Base):
    """Model table"""
    __tablename__ = "models"

    # Model name (unique identifier within provider)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Model display name
    display_name: Mapped[str] = mapped_column(String(300), nullable=False)
    
    # Model description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Model supported capabilities list (stored in JSON format)
    capabilities: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    
    # Provider-specific generation parameters (modalities, image config, tools, etc.)
    generation_config: Mapped[Dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Provider-specific generation parameters"
    )
    
    # Model status
    status: Mapped[ModelStatusEnum] = mapped_column(
        SQLEnum(ModelStatusEnum), 
        default=ModelStatusEnum.ACTIVE, 
        nullable=False
    )
    
    # Maximum context tokens
    max_context_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)

    max_output_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Provider ID (foreign key)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("model_providers.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Associated provider
    provider: Mapped["ModelProvider"] = relationship(
        "ModelProvider", 
        back_populates="models"
    )
    
    # Associated assistants
    # TODO: Commented out due to circular import issue
    # Can be retrieved via manual join query
    # assistants: Mapped[List["Assistant"]] = relationship(
    #     "Assistant",
    #     back_populates="model"
    # )

    def __repr__(self):
        return self.display_name