"""
Stateless AI Engine for LLM and Agent execution.
Decoupled from database Message persistence.
"""
import logging
import uuid
from typing import Optional, List, AsyncIterator, Dict, Any, Union
from datetime import datetime, timezone

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from src.assistants.models import Assistant
from src.ai_models.client_factory import create_chat_model
from src.chat.models import MessageRole
from src.chat.prompt_builder import PromptBuilder
from src.chat.providers.google_adapter import GoogleProviderAdapter
from src.agents.executor import AgentExecutionEngine

logger = logging.getLogger(__name__)

class AIEngine:
    """
    Stateless engine to drive Language Models and Agents.
    """
    
    def __init__(self, session=None):
        # Session is possibly used for Tool execution if tools require DB access
        # But core generation should be relatively stateless.
        self.session = session
        self.google_adapter = GoogleProviderAdapter()
        # PromptBuilder might need DB to resolve files/tools? 
        # For now, let's assume it's passed or instantiated.
        self.prompt_builder = PromptBuilder(session) if session else None

    async def generate_stream(
        self,
        assistant: Assistant,
        messages: List[Dict[str, Any]],  # Unified Message Format or LangChain Messages
        context_files: Optional[List[Dict[str, Any]]] = None, # For RAG/Prompting
        context_images: Optional[List[Dict[str, Any]]] = None,
        language: Optional[str] = None,
        context_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[dict]:
        """
        Main entry point for generating AI responses.
        Yields standard events: content_chunk, token_usage, error, agent_action.
        """
        
        # 1. Determine Execution Mode
        if assistant.enable_agent:
            # Delegate to Agent flow
             async for chunk in self._stream_agent_execution(
                assistant, messages, context_files, context_images, language, context_id, user_id
            ):
                yield chunk
        else:
            # Delegate to Simple Chat flow
            async for chunk in self._stream_simple_chat(
                assistant, messages, context_files, context_images
            ):
                yield chunk

    async def _stream_simple_chat(
        self,
        assistant: Assistant,
        chat_messages: List[Dict[str, Any]],
        context_files: Optional[List] = None,
        context_images: Optional[List] = None
    ) -> AsyncIterator[dict]:
        """
        Direct LLM Interaction (Chat Mode)
        """
        if not self.prompt_builder:
            raise ValueError("PromptBuilder required for simple chat")
            
        llm = create_chat_model(
            provider=assistant.model.provider,
            model_name=assistant.model.name,
            temperature=assistant.temperature,
            max_tokens=assistant.max_tokens,
            streaming=True
        )

        try:
            lc_messages = self._ensure_langchain_messages(chat_messages)
            
            token_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }

            async for chunk in llm.astream(lc_messages):
                content = chunk.content
                if content:
                    yield {
                        "type": "content_chunk",
                        "data": {
                            "content": content,
                            "is_final": False
                        }
                    }
                
                # Check for usage metadata
                if hasattr(chunk, 'response_metadata'):
                     usage = chunk.response_metadata.get('token_usage')
                     if usage:
                         yield {"type": "token_usage", "data": usage}
                
                # Usage metadata fallback
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage = chunk.usage_metadata
                    if isinstance(usage, dict):
                        token_usage.update(usage)

            if token_usage["total_tokens"] > 0:
                yield {
                    "type": "token_usage",
                    "data": token_usage
                }

        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            raise e

    async def _stream_agent_execution(
        self,
        assistant: Assistant,
        messages: List[Dict[str, Any]],
        files: Optional[List] = None,
        images: Optional[List] = None,
        language: Optional[str] = None,
        context_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[dict]:
        """
        Agent Execution Flow
        """
        # Get translated system prompt
        system_prompt = self.prompt_builder.get_system_prompt(assistant, language)
        
        chat_history = []
        user_input = ""
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                continue
            
            chat_history.append({
                "role": role,
                "content": content
            })
        
        if chat_history and chat_history[-1]["role"] == "user":
            user_input = chat_history.pop()["content"]
        
        agent_engine = AgentExecutionEngine(
            assistant=assistant,
            session=self.session,
            system_prompt_override=system_prompt,
            user_id=user_id,
            is_superuser=False, 
            conversation_id=str(context_id) if context_id else str(uuid.uuid4())
        )
        
        yield {
            "type": "agent_start",
            "data": {
                "max_iterations": assistant.agent_max_iterations or 10,
                "history_messages": len(chat_history)
            }
        }

        try:
            async for event in agent_engine.stream_execute(
                user_input=user_input,
                conversation_id=context_id,
                chat_history=chat_history,
                files=files
            ):
                yield event
                
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            yield {
                "type": "error",
                "data": {
                    "error": f"Agent execution failed: {str(e)}"
                }
            }


    def _ensure_langchain_messages(self, messages: List[Any]) -> List[BaseMessage]:
        """Convert varied message formats to LangChain BaseMessage"""
        result = []
        for m in messages:
            if isinstance(m, BaseMessage):
                result.append(m)
            elif isinstance(m, dict):
                role = m.get("role")
                content = m.get("content")
                if role == "user":
                    result.append(HumanMessage(content=content))
                elif role == "system":
                    result.append(SystemMessage(content=content))
                elif role == "assistant":
                    result.append(AIMessage(content=content))
        return result
