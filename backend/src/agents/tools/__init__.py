"""
Tools module initialization
"""
from .base import AgentTool, AgentToolConfig
from .registry import LocalToolRegistry, tool_registry

# Import static tools (pure functions with @tool decorator)
from .calculator import calculator
from .datetime_tool import get_current_time

# Import dynamic tools (classes that need dependency injection) - triggers @tool_registry.register
from . import knowledge_base  # noqa: F401
from . import knowledge_write  # noqa: F401
from . import http_request  # noqa: F401

# Register static tools
tool_registry.register_static("calculator", calculator)
tool_registry.register_static("get_current_time", get_current_time)

# Export all tools
__all__ = [
    "AgentTool", 
    "AgentToolConfig", 
    "LocalToolRegistry",
    "tool_registry",
    # Static tools
    "calculator",
    "get_current_time",
]
