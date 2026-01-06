import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.database import get_async_session
from src.auth.api_key_service import get_current_user_by_api_key
from src.users.models import User
from src.assistants.models import Assistant
from src.ai_models.models import Model, ModelProvider
from src.ai_models.client_factory import create_chat_model
from src.chat.prompt_builder import PromptBuilder
from src.agents.executor import AgentExecutionEngine

from .openai_schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ChatCompletionChoice,
    ChatCompletionChunkChoice,
    ChatCompletionMessage,
    ChatCompletionUsage,
    DeltaMessage
)

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_assistant_with_model(
    assistant_id: uuid.UUID,
    session: AsyncSession,
) -> Assistant:
    """Fetch assistant with loaded model and provider"""
    stmt = (
        select(Assistant)
        .where(Assistant.id == assistant_id)
        .options(selectinload(Assistant.model).selectinload(Model.provider))
    )
    result = await session.execute(stmt)
    assistant = result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assistant {assistant_id} not found"
        )
    return assistant

def convert_messages_to_langchain(messages: list, system_prompt: str = None) -> list:
    """Convert OpenAI format messages to LangChain format, injecting system prompt"""
    lc_messages = []
    
    # Inject system prompt if exists
    if system_prompt:
        lc_messages.append(SystemMessage(content=system_prompt))
        
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role == "system":
            # If user provides system prompt, we append it. 
            # Note: This might conflict with assistant system prompt depending on policy.
            # Here we allow it, as it appends after the assistant default one (or before if we adjusted order).
            lc_messages.append(SystemMessage(content=msg.content))
            
    return lc_messages

def convert_messages_to_dict(messages: list) -> list:
    """Convert OpenAI format messages to dict format for Agent Engine"""
    return [{"role": msg.role, "content": msg.content} for msg in messages]

@router.post(
    "/assistants/{assistant_id}/v1/chat/completions",
    response_model=ChatCompletionResponse,
    tags=["OpenAI Compatible"]
)
async def chat_completions(
    assistant_id: uuid.UUID,
    request: ChatCompletionRequest,
    user: User = Depends(get_current_user_by_api_key),
    session: AsyncSession = Depends(get_async_session)
):
    """
    OpenAI compatible chat completion endpoint with RAG and Agent support.
    Stateless: uses provided messages for context.
    """
    
    # 1. Fetch Assistant with Model
    stmt = (
        select(Assistant)
        .where(Assistant.id == assistant_id)
        .options(selectinload(Assistant.model).selectinload(Model.provider))
    )
    result = await session.execute(stmt)
    assistant = result.scalar_one_or_none()
    
    if not assistant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assistant not found")

    if not assistant.model or not assistant.model.provider:
         raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assistant model configuration invalid")

    model = assistant.model
    
    # Extract last user message
    if not request.messages:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Messages list cannot be empty")
        
    last_message = request.messages[-1]
    if last_message.role != "user":
        # Some clients might send system message last or assistant message?
        # Standard OpenAI flow expects User message last for a reply.
        # We will proceed but RAG might be weird if no user query.
        user_input = last_message.content
    else:
        user_input = last_message.content

    prompt_builder = PromptBuilder(session)
    completion_id = f"chatcmpl-{uuid.uuid4()}"
    created_time = int(time.time())
    model_name = model.name

    # --- AGENT MODE ---
    if assistant.enable_agent:
        # Prepare Agent Execution
        chat_history = convert_messages_to_dict(request.messages[:-1]) # All except last
        
        # Determine system prompt
        agent_engine = AgentExecutionEngine(
            assistant=assistant,
            session=session,
        )
        
        async def generate_agent_stream() -> AsyncGenerator[str, None]:
            try:
                # Agent execution
                async for event in agent_engine.stream_execute(
                    user_input=user_input,
                    chat_history=chat_history
                ):
                    # We typically only want to stream "content_chunk" to the user as the answer.
                    if event["type"] == "content_chunk":
                        content = event["data"].get("content", "")
                        if content:
                            chunk_resp = ChatCompletionChunk(
                                id=completion_id,
                                created=created_time,
                                model=model_name,
                                choices=[
                                    ChatCompletionChunkChoice(
                                        index=0,
                                        delta=DeltaMessage(role="assistant", content=content)
                                    )
                                ]
                            )
                            yield f"data: {chunk_resp.model_dump_json()}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Agent stream error: {e}", exc_info=True)
                # Yield error as a final chunk content? Or just stop.
                # Standard OpenAI behavior on mid-stream error is tricky.
                yield f"data: [DONE]\n\n"

        if request.stream:
            return StreamingResponse(
                generate_agent_stream(),
                media_type="text/event-stream"
            )
        else:
            # For non-streaming, we consume the stream and concatenate content
            full_content = ""
            async for event in agent_engine.stream_execute(
                user_input=user_input,
                chat_history=chat_history
            ):
                if event["type"] == "content_chunk":
                    full_content += event["data"].get("content", "")
            
            return ChatCompletionResponse(
                id=completion_id,
                created=created_time,
                model=model_name,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessage(role="assistant", content=full_content),
                        finish_reason="stop"
                    )
                ],
                usage=ChatCompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            )

    # --- STANDARD / RAG MODE ---
    else:
        # 1. RAG Retrieve
        rag_context = await prompt_builder.get_rag_context_content(
            assistant, 
            user_input
        )
        
        # 2. Build Prompt (with RAG injection)
        system_prompt = assistant.system_prompt or "You are a helpful AI assistant."
        if rag_context:
            system_prompt += f"\n\n{rag_context}"
            
        lc_messages = convert_messages_to_langchain(request.messages, system_prompt)
        
        # 3. Create Model
        temperature = request.temperature if request.temperature is not None else (assistant.config.get("temperature", 0.7))
        max_tokens = request.max_tokens if request.max_tokens is not None else (assistant.config.get("max_tokens"))

        lc_model = create_chat_model(
            provider=model.provider,
            model_name=model.name,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=request.stream
        )
        
        # 4. Execute
        if request.stream:
            async def generate_standard_stream() -> AsyncGenerator[str, None]:
                try:
                    async for chunk in lc_model.astream(lc_messages):
                        content = chunk.content
                        if content:
                            chunk_resp = ChatCompletionChunk(
                                id=completion_id,
                                created=created_time,
                                model=model_name,
                                choices=[
                                    ChatCompletionChunkChoice(
                                        index=0,
                                        delta=DeltaMessage(role="assistant", content=str(content))
                                    )
                                ]
                            )
                            yield f"data: {chunk_resp.model_dump_json()}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"Standard stream error: {e}", exc_info=True)
            
            return StreamingResponse(
                generate_standard_stream(),
                media_type="text/event-stream"
            )
        else:
            response = await lc_model.ainvoke(lc_messages)
            return ChatCompletionResponse(
                id=completion_id,
                created=created_time,
                model=model_name,
                choices=[
                    ChatCompletionChoice(
                        index=0,
                        message=ChatCompletionMessage(role="assistant", content=str(response.content)),
                        finish_reason="stop"
                    )
                ],
                usage=ChatCompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
            )
