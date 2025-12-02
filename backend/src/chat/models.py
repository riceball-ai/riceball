"""
Langchain-based chat models and schemas
"""
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage


class MessageRole(Enum):
    """Message role enumeration"""
    SYSTEM = "system"
    USER = "user" 
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    """Unified chat message structure
    
    content can be either:
    - str: Simple text content
    - list: Multi-modal content with mixed text and images
      Example: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]
    """
    role: MessageRole
    content: Union[str, List[Dict[str, Any]]]
    metadata: Optional[Dict[str, Any]] = None

    def to_langchain_message(self) -> BaseMessage:
        """Convert to langchain message"""
        # Use content as-is (either string or list)
        if self.role == MessageRole.SYSTEM:
            return SystemMessage(content=self.content)
        elif self.role == MessageRole.USER:
            return HumanMessage(content=self.content)
        elif self.role == MessageRole.ASSISTANT:
            return AIMessage(content=self.content)
        else:
            raise ValueError(f"Unsupported role: {self.role}")

    @classmethod
    def from_langchain_message(cls, message: BaseMessage) -> "ChatMessage":
        """Create from langchain message"""
        if isinstance(message, SystemMessage):
            role = MessageRole.SYSTEM
        elif isinstance(message, HumanMessage):
            role = MessageRole.USER
        elif isinstance(message, AIMessage):
            role = MessageRole.ASSISTANT
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")
        
        return cls(role=role, content=message.content)


@dataclass
class ChatCompletionRequest:
    """Chat completion request"""
    messages: List[ChatMessage]
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class ChatCompletionResponse:
    """Chat completion response"""
    content: str
    model: str
    token_usage: Optional[Dict[str, int]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StreamChunk:
    """Streaming response chunk"""
    content: str
    is_final: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ChatProviderError(Exception):
    """Base exception for chat provider errors"""
    pass


class ModelNotFoundError(ChatProviderError):
    """Exception raised when model is not found"""
    pass


class InvalidRequestError(ChatProviderError):
    """Exception raised for invalid requests"""
    pass


class RateLimitError(ChatProviderError):
    """Exception raised when rate limit is exceeded"""
    pass


class AuthenticationError(ChatProviderError):
    """Exception raised for authentication failures"""
    pass