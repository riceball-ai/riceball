"""
Agent Execution Engine using LangChain
"""
import logging
from typing import List, Dict, Any, AsyncIterator, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from src.assistants.models import Assistant
from src.ai_models.client_factory import create_chat_model
from .tools.base import AgentTool
from .tools.registry import tool_registry
from .mcp.manager import mcp_manager
from .mcp.tools_adapter import MCPToolAdapter
from .tools.knowledge_base import KnowledgeBaseTool
from .descriptions import get_action_description, get_observation_description, get_tool_display_name

logger = logging.getLogger(__name__)


class AgentExecutionEngine:
    """Agent execution engine using LangChain create_agent - for Assistant with tools"""
    
    def __init__(
        self, 
        assistant: Assistant, 
        session: Optional[AsyncSession] = None,
        system_prompt_override: Optional[str] = None
    ):
        self.assistant = assistant
        self.session = session
        self.system_prompt_override = system_prompt_override
        self.tools: List[AgentTool] = []
        self.llm: Optional[BaseChatModel] = None
        self.agent = None  # LangGraph compiled agent
    
    async def initialize(self):
        """Initialize agent (load LLM and tools)"""
        self.llm = self._create_llm()
        await self._load_tools()
        self.agent = self._create_agent()
    
    def _create_llm(self) -> BaseChatModel:
        """Create LLM client using create_chat_model factory"""
        model = self.assistant.model
        provider = model.provider
        
        return create_chat_model(
            provider=provider,
            model_name=model.name,
            temperature=self.assistant.temperature,
            **self.assistant.config
        )
    
    async def _load_tools(self):
        """Load all tools (local and MCP)"""
        # Load local tools
        await self._load_local_tools()
        
        # Load MCP tools
        await self._load_mcp_tools()

    async def _load_local_tools(self):
        """Load local registered tools"""
        for tool_name in self.assistant.agent_enabled_tools:
            try:
                # Special handling for knowledge_base tool
                if tool_name == "knowledge_base_query":
                    from .tools.base import AgentToolConfig
                    config = AgentToolConfig(
                        enabled=True,
                        parameters={
                            "knowledge_base_ids": self.assistant.knowledge_base_ids
                        }
                    )
                    tool = KnowledgeBaseTool(config=config, session=self.session)
                else:
                    tool = tool_registry.get_tool(tool_name)
                
                self.tools.append(tool)
                logger.info(f"Loaded local tool: {tool_name}")
            except Exception as e:
                logger.error(f"Failed to load tool {tool_name}: {e}")
    
    async def _load_mcp_tools(self):
        """Load tools from MCP servers"""
        for mcp_server in self.assistant.mcp_servers:
            if not mcp_server.is_active:
                continue
            
            try:
                # Ensure connection
                client = await mcp_manager.get_client(mcp_server.name)
                if not client or not client.is_connected:
                    # Try to connect on demand
                    logger.info(f"Connecting to MCP server {mcp_server.name} on demand...")
                    await mcp_manager.connect_server(mcp_server)
                    client = await mcp_manager.get_client(mcp_server.name)

                if not client or not client.is_connected:
                    logger.warning(f"MCP Server {mcp_server.name} unavailable. Skipping.")
                    continue
                
                # Get tools
                mcp_tool_list = await client.list_tools()
                
                # Convert to agent tools
                for tool_info in mcp_tool_list:
                    adapter = MCPToolAdapter(
                        mcp_client=client,
                        tool_info=tool_info
                    )
                    self.tools.append(adapter)
                    logger.info(f"Loaded MCP tool: {tool_info['name']} from {mcp_server.name}")
                    
            except Exception as e:
                logger.error(f"Failed to load MCP tools from {mcp_server.name}: {e}")
    
    def _create_agent(self):
        """Create LangChain agent using create_agent (v1 API)"""
        # Build system prompt
        system_prompt = self.system_prompt_override or self.assistant.system_prompt or "You are a helpful AI agent."
        
        # Convert tools to LangChain format
        langchain_tools: List[BaseTool] = []
        logger.info('self.tools:' + str(self.tools))
        for tool in self.tools:
            # Check if already a LangChain BaseTool (from @tool decorator or StructuredTool)
            if isinstance(tool, BaseTool):
                langchain_tools.append(tool)
            # Dynamic tools (AgentTool instances) need conversion
            elif hasattr(tool, 'to_langchain_tool'):
                langchain_tools.append(tool.to_langchain_tool())
            else:
                logger.warning(f"Unknown tool type: {type(tool)}")

        logger.info(f'langchain_tools: {langchain_tools}')
        
        # Create agent using v1 API
        # Note: create_agent returns a compiled LangGraph
        agent = create_agent(
            model=self.llm,
            tools=langchain_tools,
            system_prompt=system_prompt,
        )
        
        return agent
    
    async def execute(
        self, 
        user_input: str, 
        conversation_id: Optional[Any] = None,
        chat_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """Execute agent task"""
        if not self.agent:
            await self.initialize()
        
        try:
            # Build messages for the agent
            messages = []
            
            # Add chat history if available
            if chat_history:
                messages.extend(chat_history)
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Invoke the agent with messages
            result = await self.agent.ainvoke({"messages": messages})
            
            return result
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            raise
    
    async def stream_execute(
        self,
        user_input: str,
        conversation_id: Optional[Any] = None,
        chat_history: List[Dict] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream execute agent task with detailed events
        
        Yields events:
        - {"type": "agent_action", "data": {"tool": str, "input": dict, "thought": str}}
        - {"type": "agent_observation", "data": {"observation": str}}
        - {"type": "content_chunk", "data": {"content": str, "is_final": bool}}
        """
        if not self.agent:
            await self.initialize()
        
        try:
            # Build messages for the agent
            messages = []
            
            # Add chat history if available
            if chat_history:
                messages.extend(chat_history)
            
            # Add current user input
            messages.append({"role": "user", "content": user_input})
            
            # Track state
            content_buffer = ""
            current_tool_call = {}  # Track tool call being built
            token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            # Use "messages" mode to get token-by-token streaming
            # This includes tool calls, tool results, and final answers
            async for message_chunk, metadata in self.agent.astream(
                {"messages": messages},
                stream_mode="messages"
            ):
                node_name = metadata.get("langgraph_node", "")
                
                # Debug: log message chunk attributes
                logger.debug(f"Message chunk type: {type(message_chunk)}, has usage_metadata: {hasattr(message_chunk, 'usage_metadata')}")
                if hasattr(message_chunk, "usage_metadata"):
                    logger.debug(f"usage_metadata value: {message_chunk.usage_metadata}")
                
                # Extract token usage from message metadata (LangChain v1)
                # Note: In agent execution, LLM may be called multiple times (tool calls, etc.)
                # We need to accumulate token usage across all calls
                if hasattr(message_chunk, "usage_metadata") and message_chunk.usage_metadata:
                    usage = message_chunk.usage_metadata
                    if isinstance(usage, dict):
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)
                        
                        # Accumulate token usage (agent may call LLM multiple times)
                        if total_tokens > 0:
                            token_usage["input_tokens"] += input_tokens
                            token_usage["output_tokens"] += output_tokens
                            token_usage["total_tokens"] += total_tokens
                            logger.info(f"✅ Accumulated token usage: {token_usage} (this call: +{total_tokens})")
                
                # Process content_blocks
                if hasattr(message_chunk, "content_blocks") and message_chunk.content_blocks:
                    for block in message_chunk.content_blocks:
                        # Get block type and data
                        block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
                        
                        # Handle tool call chunks (from model node)
                        if block_type == "tool_call_chunk" and node_name == "model":
                            tool_id = block.get("id") if isinstance(block, dict) else getattr(block, "id", None)
                            tool_name = block.get("name") if isinstance(block, dict) else getattr(block, "name", None)
                            tool_args = block.get("args") if isinstance(block, dict) else getattr(block, "args", None)
                            
                            # Initialize or update tool call
                            if tool_id and tool_id not in current_tool_call:
                                current_tool_call[tool_id] = {"name": "", "args": ""}
                            
                            if tool_id:
                                if tool_name:
                                    current_tool_call[tool_id]["name"] = tool_name
                                if tool_args:
                                    current_tool_call[tool_id]["args"] += tool_args
                            
                            # When we have complete tool call info, emit agent_action
                            if tool_id and tool_name and current_tool_call[tool_id]["args"]:
                                try:
                                    import json
                                    # Try to parse args if complete
                                    args_dict = json.loads(current_tool_call[tool_id]["args"])
                                    
                                    description = get_action_description(tool_name, args_dict)
                                    display_name = get_tool_display_name(tool_name)
                                    
                                    yield {
                                        "type": "agent_action",
                                        "data": {
                                            "tool": tool_name,
                                            "tool_display_name": display_name,
                                            "input": args_dict,
                                            "thought": "",
                                            "description": description
                                        }
                                    }
                                    # Clear after emitting
                                    del current_tool_call[tool_id]
                                except (json.JSONDecodeError, KeyError):
                                    # Args not complete yet, continue accumulating
                                    pass
                        
                        # Handle text chunks (final answer from model node)
                        elif block_type == "text" and node_name == "model":
                            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
                            if text:
                                content_buffer += text
                                yield {
                                    "type": "content_chunk",
                                    "data": {
                                        "content": text,
                                        "is_final": False
                                    }
                                }
                        
                        # Handle tool results (from tools node)
                        elif block_type == "text" and node_name == "tools":
                            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
                            if text:
                                # Tool name might be in message attributes
                                tool_name = getattr(message_chunk, "name", "unknown_tool")
                                
                                description = get_observation_description(tool_name, text)
                                display_name = get_tool_display_name(tool_name)
                                
                                yield {
                                    "type": "agent_observation",
                                    "data": {
                                        "tool": tool_name,
                                        "tool_display_name": display_name,
                                        "observation": text,
                                        "description": description
                                    }
                                }
            
            # Send final marker if we received any content
            if content_buffer:
                yield {
                    "type": "content_chunk",
                    "data": {
                        "content": "",
                        "is_final": True
                    }
                }
            
            # Send token usage information
            logger.info(f"Final token usage: {token_usage}")
            if token_usage["total_tokens"] > 0:
                yield {
                    "type": "token_usage",
                    "data": token_usage
                }
                
        except Exception as e:
            logger.error(f"Agent streaming error: {e}")
            logger.error(f"User input: {user_input[:100]}...")  # Log first 100 chars
            logger.error(f"Assistant: {self.assistant.name}, Model: {self.assistant.model.name}")
            raise
