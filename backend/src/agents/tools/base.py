"""
Base classes for Agent tools
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from langchain.tools import tool


class AgentToolConfig(BaseModel):
    """Tool configuration base class"""
    enabled: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentTool(ABC):
    """Agent tool base class"""
    
    def __init__(self, config: Optional[AgentToolConfig] = None):
        self.config = config or AgentToolConfig()
        self._langchain_tool = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute tool"""
        pass
    
    def to_langchain_tool(self):
        """Convert to LangChain tool using @tool decorator (v1)"""
        if self._langchain_tool is None:
            self._langchain_tool = self._create_langchain_tool()
        return self._langchain_tool
    
    def _create_langchain_tool(self):
        """Create LangChain tool instance using @tool decorator"""
        import inspect
        from pydantic import create_model
        
        # Get execute method signature to create input schema
        sig = inspect.signature(self.execute)
        
        # Build pydantic model fields for input schema
        fields = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Determine field type and default
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            if param.default != inspect.Parameter.empty:
                fields[param_name] = (param_type, param.default)
            else:
                fields[param_name] = (param_type, ...)
        
        # Create input schema model
        InputSchema = create_model(
            f"{self.name}_input",
            **fields
        )
        
        # Create wrapper function for the tool
        async def tool_func(**kwargs):
            return await self.execute(**kwargs)
        
        # Apply @tool decorator dynamically (LangChain v1)
        # First parameter is name, then pass other parameters
        return tool(
            self.name,  # name_or_callable parameter
            description=self.description,
            args_schema=InputSchema
        )(tool_func)
