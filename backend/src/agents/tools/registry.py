"""
Local tool registry for managing built-in tools
"""
from typing import Dict, List, Type, Union, Callable
from .base import AgentTool, AgentToolConfig


class LocalToolRegistry:
    """Registry for local (built-in) tools - supports both static functions and dynamic classes"""
    
    # Dynamic tools (classes that need dependency injection)
    _tools: Dict[str, Type[AgentTool]] = {}
    
    # Static tools (pure functions decorated with @tool)
    _static_tools: Dict[str, Callable] = {}
    
    @classmethod
    def register(cls, tool_class: Type[AgentTool]):
        """Register a tool class (for dynamic tools that need dependency injection)"""
        # Get tool name from an instance
        temp_instance = tool_class()
        cls._tools[temp_instance.name] = tool_class
        return tool_class
    
    @classmethod
    def register_static(cls, name: str, tool_func: Callable):
        """Register a static tool function (decorated with @tool)"""
        cls._static_tools[name] = tool_func
        return tool_func
    
    @classmethod
    def get_tool(cls, tool_name: str, config: AgentToolConfig = None) -> Union[AgentTool, Callable]:
        """Get a tool instance by name (returns AgentTool or static function)"""
        # Check static tools first
        if tool_name in cls._static_tools:
            return cls._static_tools[tool_name]
        
        # Check dynamic tools
        tool_class = cls._tools.get(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        return tool_class(config or AgentToolConfig())
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """List all registered tool names"""
        return list(cls._static_tools.keys()) + list(cls._tools.keys())
    
    @classmethod
    def get_tool_info(cls, tool_name: str) -> Dict[str, str]:
        """Get tool information (name and description)"""
        # Check static tools
        if tool_name in cls._static_tools:
            tool_func = cls._static_tools[tool_name]
            return {
                "name": tool_func.name,
                "description": tool_func.description
            }
        
        # Check dynamic tools
        tool_class = cls._tools.get(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        # Create temporary instance to get name and description
        temp_instance = tool_class()
        return {
            "name": temp_instance.name,
            "description": temp_instance.description
        }
    
    @classmethod
    def list_tools_with_info(cls) -> List[Dict[str, str]]:
        """List all tools with their information"""
        tools_info = []
        for tool_name in cls.list_tools():
            try:
                info = cls.get_tool_info(tool_name)
                tools_info.append(info)
            except Exception:
                # Skip tools that fail to initialize
                continue
        return tools_info
    
    @classmethod
    def create_tools(cls, tool_names: List[str], configs: Dict[str, AgentToolConfig] = None) -> List[Union[AgentTool, Callable]]:
        """Create multiple tool instances"""
        configs = configs or {}
        tools = []
        for name in tool_names:
            config = configs.get(name, AgentToolConfig())
            tool = cls.get_tool(name, config)
            tools.append(tool)
        return tools


# Global registry instance
tool_registry = LocalToolRegistry()
