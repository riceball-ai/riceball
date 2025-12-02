"""
MCP Tools Adapter - Convert MCP tools to Agent tools
"""
from typing import Any, Dict, Optional
from pydantic import create_model, Field

from langchain_core.tools import StructuredTool

from .client import MCPClient
from ..tools.base import AgentTool, AgentToolConfig


class MCPToolAdapter(AgentTool):
    """Adapter to convert MCP tools to Agent tools"""
    
    def __init__(
        self, 
        mcp_client: MCPClient, 
        tool_info: Dict[str, Any], 
        config: Optional[AgentToolConfig] = None
    ):
        super().__init__(config)
        self.mcp_client = mcp_client
        self.tool_info = tool_info
        self._name = tool_info["name"]
        self._description = tool_info.get("description", "")
        self._input_schema = tool_info.get("inputSchema", {})
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    async def execute(self, **kwargs) -> Any:
        """Execute MCP tool"""
        try:
            result = await self.mcp_client.call_tool(self._name, kwargs)
            
            # Extract content from result
            if hasattr(result, 'content'):
                # Handle list of content items
                if isinstance(result.content, list):
                    content_parts = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            content_parts.append(item.text)
                        else:
                            content_parts.append(str(item))
                    return "\n".join(content_parts)
                else:
                    return str(result.content)
            
            return str(result)
            
        except Exception as e:
            return f"Error executing MCP tool {self._name}: {str(e)}"
    
    def _create_langchain_tool(self) -> StructuredTool:
        """Convert to LangChain tool"""
        async def tool_func(**kwargs):
            return await self.execute(**kwargs)
        
        # Build args schema from JSON Schema
        args_schema = self._build_args_schema(self._input_schema)
        
        return StructuredTool.from_function(
            coroutine=tool_func,
            name=self._name,
            description=self._description,
            args_schema=args_schema
        )
    
    def _build_args_schema(self, schema: Dict[str, Any]):
        """Build Pydantic model from JSON Schema"""
        if not schema:
            return None
        
        fields = {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        for prop_name, prop_info in properties.items():
            field_type = self._json_type_to_python(prop_info.get("type", "string"))
            default = ... if prop_name in required else None
            description = prop_info.get("description", "")
            
            fields[prop_name] = (
                field_type, 
                Field(default=default, description=description)
            )
        
        if not fields:
            return None
        
        return create_model(f"{self._name}Args", **fields)
    
    @staticmethod
    def _json_type_to_python(json_type: str):
        """Convert JSON Schema type to Python type"""
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_mapping.get(json_type, str)
