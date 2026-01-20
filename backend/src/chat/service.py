"""
Langchain-based chat service
"""
import base64
import binascii
import hashlib
import json
import logging
import uuid
from io import BytesIO
from typing import Optional, List, AsyncIterator, Any, Dict
from datetime import datetime, timezone, timedelta
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, attributes as orm_attributes

from src.assistants.models import Assistant, Conversation, Message, MessageTypeEnum
from src.ai_models.models import Model
from src.ai_models.client_factory import create_chat_model
from src.system_config.service import config_service
from src.files.storage import storage_service
from src.services.cache import get_cache_service

from .models import ChatMessage, MessageRole
from .conversation_service import ConversationService
from .prompt_builder import PromptBuilder
from .providers.google_adapter import GoogleProviderAdapter

logger = logging.getLogger(__name__)


class LangchainChatService:
    """Chat service using langchain for AI interactions"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_service = ConversationService(session)
        self.google_adapter = GoogleProviderAdapter()
        self.prompt_builder = PromptBuilder(
            session=session,
            google_adapter=self.google_adapter,
        )

    async def _store_inline_media_to_s3(
        self,
        *,
        base64_data: str,
        mime_type: str
    ) -> Optional[dict[str, Any]]:
        """Persist inline media blob to S3 and return metadata for downstream usage."""
        logger.debug(f"_store_inline_media_to_s3 called with mime_type={mime_type}, data_len={len(base64_data) if base64_data else 0}")
        if not base64_data:
            logger.warning("Empty base64_data provided to _store_inline_media_to_s3")
            return None

        try:
            binary_data = base64.b64decode(base64_data)
            logger.debug(f"Decoded {len(binary_data)} bytes from base64")
        except (binascii.Error, ValueError) as e:
            logger.warning(f"Failed to decode inline media payload from Gemini response: {e}")
            return None

        file_id = uuid.uuid4()
        subtype = ""
        if "/" in mime_type:
            subtype = mime_type.split("/", 1)[1].split(";", 1)[0]
        filename = f"{file_id}.{subtype}" if subtype else str(file_id)

        buffer = BytesIO(binary_data)
        buffer.seek(0)

        try:
            file_key = await storage_service.upload_file(
                file_data=buffer,
                file_type="ai-generated",
                file_id=file_id,
                filename=filename,
                content_type=mime_type,
                file_size=len(binary_data)
            )
            public_url = await storage_service.get_public_url(file_key)
            return {
                "file_key": file_key,
                "url": public_url,
                "size": len(binary_data),
                "content_type": mime_type,
            }
        except Exception as exc:
            logger.error("Failed to upload inline media to S3: %s", exc, exc_info=True)
            return None

    async def _store_gemini_parts_snapshot(
        self,
        *,
        parts: List[Dict[str, Any]]
    ) -> Optional[dict[str, Any]]:
        """Persist sanitized Gemini response parts JSON to S3."""
        if not parts:
            return None

        try:
            payload = json.dumps(parts).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.error("Failed to serialize Gemini parts payload: %s", exc)
            return None

        file_id = uuid.uuid4()
        filename = f"{file_id}.json"
        buffer = BytesIO(payload)
        buffer.seek(0)

        try:
            file_key = await storage_service.upload_file(
                file_data=buffer,
                file_type="gemini-parts",
                file_id=file_id,
                filename=filename,
                content_type="application/json",
                file_size=len(payload)
            )
            public_url = await storage_service.get_public_url(file_key)
            return {
                "file_key": file_key,
                "url": public_url,
                "size": len(payload),
                "content_type": "application/json",
            }
        except Exception as exc:
            logger.error("Failed to upload Gemini parts snapshot to S3: %s", exc, exc_info=True)
            return None
    
    async def create_conversation(
        self, 
        assistant_id: uuid.UUID, 
        user_id: uuid.UUID,
        title: Optional[str] = None
    ) -> Conversation:
        return await self.conversation_service.create_conversation(
            assistant_id=assistant_id,
            user_id=user_id,
            title=title,
        )
    
    async def get_conversation(
        self, 
        conversation_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[Conversation]:
        return await self.conversation_service.get_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )
    
    async def get_conversation_messages(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Message]:
        return await self.conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def _prepare_image_attachments(
        self,
        raw_images: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Create prompt + storage payloads for user-provided images."""
        prompt_payloads: List[Dict[str, Any]] = []
        stored_payloads: List[Dict[str, Any]] = []

        for index, image in enumerate(raw_images):
            if not isinstance(image, dict):
                logger.debug("Skipping non-dict image attachment at index %s", index)
                continue

            sanitized = self._sanitize_single_image(image, index)
            if not sanitized:
                continue

            stored_payloads.append(sanitized)
            prompt_payload = dict(image)
            prompt_payload.update(sanitized)
            prompt_payloads.append(prompt_payload)

        return prompt_payloads, stored_payloads

    def _sanitize_single_image(
        self,
        image: Dict[str, Any],
        index: int,
    ) -> Optional[Dict[str, Any]]:
        url = image.get("url")
        file_key = (
            image.get("file_key")
            or image.get("fileKey")
            or image.get("file_path")
            or image.get("filePath")
        )

        data_url = image.get("data_url") or image.get("dataUrl")
        if not url and data_url and data_url.startswith("http"):
            url = data_url

        if not url and not file_key:
            logger.warning(
                "Skipping image attachment %s: missing both url and file reference",
                index,
            )
            return None

        sanitized: Dict[str, Any] = {
            "id": str(image.get("id") or uuid.uuid4()),
        }
        if url:
            sanitized["url"] = url
        if file_key:
            sanitized["file_key"] = file_key

        mime_value = (
            image.get("mime_type")
            or image.get("mimeType")
            or image.get("content_type")
            or image.get("contentType")
        )
        if mime_value:
            sanitized["mime_type"] = mime_value

        if image.get("alt"):
            sanitized["alt"] = image["alt"]
        size_value = image.get("size")
        if isinstance(size_value, (int, float)):
            sanitized["size"] = size_value
        if image.get("source"):
            sanitized["source"] = image["source"]

        return sanitized
    

    async def send_message_stream(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        content: str,
        images: Optional[List[Dict[str, Any]]] = None,
        language: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """Send a message and get streaming AI response (supports Agent mode)"""
        conversation = await self.conversation_service.get_conversation_with_model(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        
        if not conversation:
            raise ValueError("Conversation not found or access denied")

        # Prepare image attachments for prompting + persistence
        prompt_images: Optional[List[Dict[str, Any]]] = None
        user_extra_data: Dict[str, Any] = {}
        if images:
            prompt_images, stored_images = self._prepare_image_attachments(images)
            if stored_images:
                user_extra_data["images"] = stored_images
        else:
            stored_images = None
        
        # Explicitly set created_at to ensure proper ordering
        # Add a small delay to assistant message to ensure it appears after user message
        now = datetime.now(timezone.utc)
        
        user_message = Message(
            content=content,
            message_type=MessageTypeEnum.USER,
            conversation_id=conversation_id,
            user_id=user_id,
            extra_data=user_extra_data if user_extra_data else None,
            created_at=now
        )
        
        assistant_message = Message(
            content="",  # Will be updated after streaming
            message_type=MessageTypeEnum.ASSISTANT,
            conversation_id=conversation_id,
            extra_data={"model": conversation.assistant.model.name},
            created_at=now + timedelta(milliseconds=10)
        )
        
        self.session.add(user_message)
        self.session.add(assistant_message)
        await self.session.flush()  # Get IDs
        
        # Variables to store streaming results
        content_chunks = []
        media_outputs: List[Dict[str, Any]] = []
        full_response_parts: List[Dict[str, Any]] = []  # For Gemini multi-turn editing
        full_response_parts_ref: Optional[Dict[str, Any]] = None
        error_occurred = False
        error_message = ""
        agent_execution_log = []  # Store agent thought chain (only for agent mode)
        token_usage = None  # Store token usage information
        exclude_ids = [user_message.id, assistant_message.id]

        try:
            # Choose streaming method based on mode
            if conversation.assistant.enable_agent:
                # Agent mode: use agent execution engine with tools
                stream_generator = self._stream_agent_response(
                    conversation.assistant,
                    content,
                    conversation,
                    assistant_message.id,
                    exclude_ids,
                    language=language
                )
            else:
                # Non-agent mode: direct LLM chat with optional RAG
                # Yield assistant message start event
                yield {
                    "type": "assistant_message_start",
                    "data": {
                        "id": str(assistant_message.id),
                        "conversation_id": str(conversation_id),
                        "message_type": "ASSISTANT",
                        "model": conversation.assistant.model.name,
                        "created_at": assistant_message.created_at.isoformat()
                    }
                }
                
                chat_messages = await self.build_prompt_messages(
                    conversation,
                    content,
                    exclude_ids,
                    current_images=prompt_images,
                    language=language,
                )
                stream_generator = self._stream_ai_response(conversation.assistant, chat_messages, conversation_id=conversation_id)
            
            # Process streaming events (unified handling for both modes)
            async for chunk_data in stream_generator:
                # Track agent execution steps (agent mode only)
                if chunk_data["type"] == "agent_action":
                    agent_execution_log.append(chunk_data["data"])
                
                # Collect content chunks (both modes)
                if chunk_data["type"] == "content_chunk":
                    chunk_content = chunk_data["data"].get("content", "")
                    if chunk_content:
                        content_chunks.append(chunk_content)
                    chunk_media = chunk_data["data"].get("media")
                    if chunk_media:
                        logger.info(f"Collecting {len(chunk_media)} media items from chunk")
                        media_outputs.extend(chunk_media)
                        logger.info(f"Total media_outputs now: {len(media_outputs)}")
                
                # Collect token usage (both modes)
                if chunk_data["type"] == "token_usage":
                    token_usage = chunk_data["data"]
                
                # Collect full response parts for Gemini (for multi-turn editing)
                if chunk_data["type"] == "full_response_parts":
                    payload = chunk_data["data"]
                    full_response_parts = payload.get("parts", [])
                    full_response_parts_ref = payload.get("storage")
                
                # Forward all events to client (except internal full_response_parts)
                if chunk_data["type"] != "full_response_parts":
                    yield chunk_data
        
        except asyncio.CancelledError:
            logger.warning(f"Streaming cancelled by client for conversation {conversation_id}")
            try:
                await self.session.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            logger.error(f"Streaming error: {error_message}")
            
        # After all streaming is complete, handle database operations and final response
        if error_occurred:
            # Rollback any pending changes
            try:
                await self.session.rollback()
            except Exception:
                pass
            
            yield {
                "type": "error",
                "data": {
                    "error": error_message,
                    "conversation_id": str(conversation_id)
                }
            }
        else:
            # Success case - update database and send completion
            complete_content = "".join(content_chunks)
            
            assistant_message.content = complete_content
            
            # Store agent execution log if available
            if agent_execution_log:
                assistant_message.extra_data["agent_execution"] = agent_execution_log

            logger.info(f"Preparing to save message. media_outputs length: {len(media_outputs)}")
            if media_outputs:
                logger.info(f"Saving {len(media_outputs)} media items to assistant_message.extra_data")
                assistant_message.extra_data["media"] = media_outputs
                # Mark extra_data as modified for SQLAlchemy to detect changes
                orm_attributes.flag_modified(assistant_message, "extra_data")
                logger.info(f"assistant_message.extra_data after assignment: {assistant_message.extra_data}")
            
            # Save Gemini response metadata for multi-turn editing (prefer S3 snapshot)
            if self.google_adapter.is_google_provider(conversation.assistant):
                if full_response_parts_ref:
                    assistant_message.extra_data["gemini_response_parts_ref"] = full_response_parts_ref
                    orm_attributes.flag_modified(assistant_message, "extra_data")
                    logger.info("Saved Gemini response parts reference to S3 (file_key=%s)", full_response_parts_ref.get("file_key"))
                elif full_response_parts:
                    assistant_message.extra_data["gemini_response_parts"] = full_response_parts
                    orm_attributes.flag_modified(assistant_message, "extra_data")
                    logger.info(
                        "Saved %s Gemini response parts inline (fallback mode)",
                        len(full_response_parts)
                    )

            # Update conversation metadata
            conversation.last_message_at = datetime.now(timezone.utc)
            conversation.message_count = conversation.message_count + 2
            
            # Always yield completion (with or without DB update success)
            completion_data = {
                "type": "assistant_message_complete",
                "data": {
                    "id": str(assistant_message.id),
                    "content": complete_content,
                    "conversation_id": str(conversation_id),
                    "message_type": "ASSISTANT",
                    "model": conversation.assistant.model.name,
                    "created_at": assistant_message.created_at.isoformat(),
                    "updated_at": assistant_message.updated_at.isoformat(),
                    "user_message_id": str(user_message.id)
                }
            }
            
            if media_outputs:
                logger.info(f"Adding {len(media_outputs)} media items to completion_data")
                completion_data["data"]["media"] = media_outputs

            # Add token usage to completion data if available
            if token_usage:
                completion_data["data"]["token_usage"] = token_usage

            completion_data["data"]["extra_data"] = assistant_message.extra_data
            logger.info(f"Final completion_data keys: {list(completion_data['data'].keys())}")
            logger.info(f"Completion extra_data.media length: {len(completion_data['data'].get('extra_data', {}).get('media', []))}")
            
            # Record token usage - this will also update conversation totals in billing service
            if token_usage and token_usage.get("total_tokens", 0) > 0:
                # Token usage recording removed - billing system no longer exists
                pass
            
            # Commit all updates together (message, conversation, and token usage)
            await self.session.commit()

            yield completion_data



    async def build_prompt_messages(
        self,
        conversation: Conversation,
        user_input: str,
        exclude_message_ids: Optional[List[uuid.UUID]] = None,
        current_images: Optional[List[Dict[str, Any]]] = None,
        language: Optional[str] = None,
    ) -> List[ChatMessage]:
        """Delegate prompt construction to PromptBuilder for reuse."""
        return await self.prompt_builder.build_prompt_messages(
            conversation=conversation,
            user_input=user_input,
            exclude_message_ids=exclude_message_ids,
            current_images=current_images,
            language=language,
        )

    async def _stream_agent_response(
        self,
        assistant: Assistant,
        user_input: str,
        conversation: Conversation,
        assistant_message_id: uuid.UUID,
        exclude_message_ids: Optional[List[uuid.UUID]] = None,
        language: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        Stream Agent execution response with thought chain and history support
        
        Yields chunks in the format:
        - {"type": "agent_action", "data": {"tool": str, "input": dict, "thought": str}}
        - {"type": "agent_observation", "data": {"observation": str}}
        - {"type": "content_chunk", "data": {"content": str, "is_final": bool}}
        - {"type": "token_usage", "data": {"input_tokens": int, "output_tokens": int, "total_tokens": int}}
        """
        from src.agents.executor import AgentExecutionEngine
        
        # Build chat history using the same method as non-agent mode
        # This ensures consistent token management and history handling
        chat_messages = await self.build_prompt_messages(
            conversation, 
            user_input, 
            exclude_message_ids,
            language=language
        )
        
        # Convert ChatMessage to dict format for agent
        # Agent expects [{"role": "user", "content": "..."}, ...]
        # Skip system messages as they're handled separately in agent
        chat_history = []
        for msg in chat_messages:
            if msg.role != MessageRole.SYSTEM:  # System prompt already in assistant config
                chat_history.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        # Remove the last user message (current input) from history
        # as it will be passed separately to stream_execute
        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop()
        
        # Get translated system prompt
        system_prompt = self.prompt_builder.get_system_prompt(assistant, language)
        
        # Initialize Agent execution engine
        agent_engine = AgentExecutionEngine(
            assistant=assistant,
            session=self.session,
            system_prompt_override=system_prompt,
            user_id=conversation.user_id,
            is_superuser=conversation.user.is_superuser if conversation.user else False
        )
        
        # Yield agent start event
        yield {
            "type": "agent_start",
            "data": {
                "assistant_message_id": str(assistant_message_id),
                "max_iterations": assistant.agent_max_iterations or 10,
                "history_messages": len(chat_history)
            }
        }
        
        try:
            # Stream agent execution with history
            async for event in agent_engine.stream_execute(
                user_input=user_input,
                conversation_id=conversation.id,
                chat_history=chat_history
            ):
                # Forward agent events to client
                yield event
                
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            yield {
                "type": "error",
                "data": {
                    "error": f"Agent execution failed: {str(e)}"
                }
            }
    

    async def _stream_gemini_native(
        self,
        assistant: Assistant,
        messages: List[ChatMessage],
        conversation_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[dict]:
        """Stream Gemini response using google-genai SDK to preserve thought_signature"""
        from google import genai

        provider = assistant.model.provider
        if not provider or not provider.api_key:
            raise ValueError("Google model missing API Key configuration")

        contents, system_instruction = self.google_adapter.build_contents_payload(messages, assistant)
        if not contents:
            raise ValueError("No content to send to Gemini")

        overrides: Dict[str, Any] = {}
        if assistant.temperature is not None:
            overrides["temperature"] = assistant.temperature

        generation_config = self.google_adapter.build_generation_config(
            assistant,
            overrides=overrides or None,
            system_instruction=system_instruction,
        )

        try:
            client = genai.Client(api_key=provider.api_key)
        except Exception as exc:  # pragma: no cover - defensive init guard
            logger.error("Failed to initialize Google Gemini client: %s", exc, exc_info=True)
            raise ValueError("Cannot initialize Gemini client") from exc

        request_kwargs = {
            "model": assistant.model.name,
            "contents": contents,
            "config": generation_config,
        }

        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        media_counter = 0
        full_response_parts: List[Dict[str, Any]] = []
        inline_storage_map: Dict[str, Dict[str, Any]] = {}
        sanitized_response_parts: Optional[List[Dict[str, Any]]] = None
        parts_storage_ref: Optional[Dict[str, Any]] = None

        try:
            response_stream = await client.aio.models.generate_content_stream(**request_kwargs)
        except Exception as exc:  # pragma: no cover - network/init errors
            logger.error("Failed to start Gemini stream: %s", exc, exc_info=True)
            raise ValueError("Gemini API call failed, cannot start streaming response") from exc

        cache = get_cache_service()
        
        try:
            async for chunk in response_stream:
                # Check for stop signal
                if conversation_id and await cache.exists(f"stop_signal:{conversation_id}"):
                    # Clean up signal
                    await cache.delete(f"stop_signal:{conversation_id}")
                    break

                candidates = getattr(chunk, "candidates", None)
                if not candidates:
                    continue

                candidate = candidates[0]

                usage = getattr(chunk, "usage_metadata", None)
                if usage:
                    token_usage["input_tokens"] = (
                        getattr(usage, "prompt_token_count", None)
                        or getattr(usage, "input_token_count", None)
                        or getattr(usage, "prompt_tokens", None)
                        or getattr(usage, "input_tokens", None)
                        or 0
                    )
                    token_usage["output_tokens"] = (
                        getattr(usage, "candidates_token_count", None)
                        or getattr(usage, "output_token_count", None)
                        or getattr(usage, "output_tokens", None)
                        or 0
                    )
                    token_usage["total_tokens"] = (
                        getattr(usage, "total_token_count", None)
                        or getattr(usage, "total_tokens", None)
                        or token_usage["input_tokens"] + token_usage["output_tokens"]
                    )

                if not candidate.content or not candidate.content.parts:
                    continue

                for part in candidate.content.parts:
                    inline_data_obj = getattr(part, "inline_data", None)
                    base64_data = ""
                    inline_hash = None
                    inline_mime_type = getattr(inline_data_obj, "mime_type", "application/octet-stream")
                    if inline_data_obj and getattr(inline_data_obj, "data", None):
                        raw_payload = inline_data_obj.data
                        if isinstance(raw_payload, bytes):
                            base64_data = base64.b64encode(raw_payload).decode("utf-8")
                        elif isinstance(raw_payload, str):
                            base64_data = raw_payload
                        else:
                            logger.warning("Unsupported inline_data payload type: %s", type(raw_payload))
                            base64_data = ""
                        inline_hash = self._hash_base64_payload(base64_data)

                    part_dict = self.google_adapter.serialize_part(part)
                    if part_dict:
                        if inline_hash:
                            inline_section = part_dict.get("inline_data")
                            if inline_section:
                                inline_section["data_hash"] = inline_hash
                            image_section = part_dict.get("image_url")
                            if image_section:
                                image_section["data_hash"] = inline_hash
                        full_response_parts.append(part_dict)

                    text_value = getattr(part, "text", None)
                    if text_value:
                        yield {
                            "type": "content_chunk",
                            "data": {
                                "content": text_value,
                                "is_final": False,
                            },
                        }

                    if base64_data:
                        storage_info = await self._store_inline_media_to_s3(
                            base64_data=base64_data,
                            mime_type=inline_mime_type,
                        )
                        if storage_info:
                            if inline_hash:
                                inline_storage_map[inline_hash] = {
                                    **storage_info,
                                    "mime_type": inline_mime_type,
                                }
                            media_counter += 1
                            content_type = storage_info.get("content_type") or inline_mime_type
                            media_entry = {
                                "id": f"media-{media_counter}",
                                "type": "image" if content_type.startswith("image/") else "binary",
                                "mime_type": content_type,
                                "url": storage_info.get("url"),
                                "storage": storage_info,
                                "index": media_counter,
                            }
                            yield {
                                "type": "content_chunk",
                                "data": {
                                    "content": "",
                                    "is_final": False,
                                    "media": [media_entry],
                                },
                            }

        except Exception as exc:
            logger.error("Gemini native stream response failed: %s", exc, exc_info=True)
            raise ValueError(f"Gemini API error: {exc}") from exc

        if full_response_parts:
            sanitized_response_parts = self.google_adapter.prepare_parts_for_storage(
                full_response_parts,
                inline_storage_map,
            )
            parts_storage_ref = await self._store_gemini_parts_snapshot(
                parts=sanitized_response_parts
            )

        yield {
            "type": "content_chunk",
            "data": {
                "content": "",
                "is_final": True,
            },
        }

        if token_usage["total_tokens"] > 0:
            yield {
                "type": "token_usage",
                "data": token_usage,
            }

        if sanitized_response_parts:
            parts_payload = {"parts": sanitized_response_parts}
            if parts_storage_ref:
                parts_payload["storage"] = parts_storage_ref
            yield {
                "type": "full_response_parts",
                "data": parts_payload,
            }
            logger.info("Collected %s Gemini parts, including thought_signature", len(full_response_parts))
    
    @staticmethod
    def _hash_base64_payload(payload: str) -> Optional[str]:
        """Return stable hash for inline payloads so we can map to S3 objects."""
        if not payload:
            return None
        try:
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Hashing inline payload failed: %s", exc)
            return None

    async def _stream_ai_response(
        self,
        assistant: Assistant,
        messages: List[ChatMessage],
        conversation_id: Optional[uuid.UUID] = None
    ) -> AsyncIterator[dict]:
        """Stream AI response using LangChain clients directly with token usage tracking"""
        
        # For Gemini: Use native SDK to preserve thought_signature
        if self.google_adapter.is_google_provider(assistant):
            async for event in self._stream_gemini_native(assistant, messages, conversation_id=conversation_id):
                yield event
            # End of Gemini path
            return  # This is fine - empty return in async generator
        
        # For other providers: Use LangChain
        provider = assistant.model.provider
        
        def _merge_generation_params(*param_dicts: Optional[dict]) -> dict:
            """Merge provider-level and assistant-level generation parameters."""
            merged: dict[str, Any] = {}
            for params in param_dicts:
                if not params:
                    continue
                for key, value in params.items():
                    if value is None:
                        continue
                    merged[key] = value
            return merged

        model_generation_config = getattr(assistant.model, "generation_config", None)
        assistant_overrides = (assistant.config or {}).get("additional_params", {})
        generation_params = _merge_generation_params(model_generation_config, assistant_overrides)

        if self.google_adapter.is_google_provider(assistant):
            generation_params = self.google_adapter.normalize_generation_params(generation_params, assistant)

        # Create LangChain client
        try:
            client = create_chat_model(
                provider=provider,
                model_name=assistant.model.name,
                temperature=assistant.temperature,
                **generation_params
            )
        except Exception as e:
            raise ValueError(f"Failed to create chat client: {str(e)}")
        
        # Convert ChatMessage to LangChain messages
        lc_messages = [msg.to_langchain_message() for msg in messages]
        
        # Track token usage
        token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        media_counter = 0
        
        # Collect full response parts for Gemini (includes thought_signature)
        # This is critical for multi-turn image editing
        full_response_parts: List[Dict[str, Any]] = []

        def _register_media_payload(
            *,
            mime_type: str,
            origin: str,
            url: Optional[str] = None,
            data_url: Optional[str] = None,
            storage_info: Optional[dict[str, Any]] = None
        ) -> dict[str, Any]:
            """Normalize media metadata for downstream consumers."""
            nonlocal media_counter
            media_counter += 1
            entry: dict[str, Any] = {
                "id": f"media-{media_counter}",
                "type": "image" if mime_type.startswith("image/") else "binary",
                "mime_type": mime_type,
                "alt": f"Generated image {media_counter}" if mime_type.startswith("image/") else mime_type,
                "index": media_counter,
                "source": origin
            }
            if url:
                entry["url"] = url
            elif data_url:
                entry["data_url"] = data_url
            if storage_info:
                entry["storage"] = storage_info
            return entry

        def _media_markdown(entry: dict[str, Any]) -> str:
            """Render lightweight placeholder for media to avoid huge prompts."""
            # Don't add placeholder text - frontend will render media from the media array
            return ""

        async def _extract_content_and_media(content_part: Any) -> tuple[str, List[Dict[str, Any]]]:
            """Normalize LangChain chunk content and capture inline media."""
            text_segments: List[str] = []
            chunk_media: List[Dict[str, Any]] = []

            async def _walk(part: Any) -> None:
                if part is None:
                    return
                if isinstance(part, str):
                    text_segments.append(part)
                    return
                if isinstance(part, list):
                    for item in part:
                        await _walk(item)
                    return
                if isinstance(part, dict):
                    # Log dict structure for debugging
                    logger.debug(f"Processing dict part with keys: {list(part.keys())}")
                    
                    # Nested parts from Google responses
                    nested_parts = part.get("parts")
                    if nested_parts:
                        logger.debug(f"Found nested parts: {nested_parts}")
                        await _walk(nested_parts)

                    text_value = part.get("text")
                    if text_value:
                        text_segments.append(text_value)

                    inline_data = part.get("inline_data") or part.get("inlineData")
                    if inline_data:
                        logger.debug(f"Found inline_data in chunk: {list(inline_data.keys())}")
                        mime_type = inline_data.get("mime_type") or inline_data.get("mimeType") or "application/octet-stream"
                        data = inline_data.get("data")
                        if data:
                            logger.info(f"Attempting to upload inline media to S3 (mime: {mime_type}, size: {len(data)} chars)")
                            storage_info = await self._store_inline_media_to_s3(
                                base64_data=data,
                                mime_type=mime_type
                            )
                            logger.info(f"S3 upload result: {storage_info is not None}")
                            if storage_info:
                                media_entry = _register_media_payload(
                                    mime_type=mime_type,
                                    origin="inline_data",
                                    url=storage_info.get("url"),
                                    storage_info=storage_info
                                )
                            else:
                                data_url = f"data:{mime_type};base64,{data}"
                                media_entry = _register_media_payload(
                                    mime_type=mime_type,
                                    origin="inline_data",
                                    data_url=data_url
                                )
                            chunk_media.append(media_entry)
                            placeholder = _media_markdown(media_entry)
                            if placeholder:
                                text_segments.append(placeholder)

                    image_url = part.get("image_url") or part.get("imageUrl")
                    if image_url:
                        if isinstance(image_url, dict):
                            url_value = image_url.get("url")
                        else:
                            url_value = image_url
                        if url_value:
                            # Check if it's a data URL that needs to be uploaded to S3
                            if url_value.startswith("data:"):
                                logger.info("Found data URL in image_url, uploading to S3")
                                # Extract mime type and base64 data from data URL
                                # Format: data:image/jpeg;base64,<base64_data>
                                try:
                                    header, base64_data = url_value.split(",", 1)
                                    mime_type = header.split(":")[1].split(";")[0] if ":" in header else "image/*"
                                    
                                    logger.info(f"Uploading image_url data to S3 (mime: {mime_type}, size: {len(base64_data)} chars)")
                                    storage_info = await self._store_inline_media_to_s3(
                                        base64_data=base64_data,
                                        mime_type=mime_type
                                    )
                                    logger.info(f"S3 upload result: {storage_info is not None}")
                                    
                                    if storage_info:
                                        media_entry = _register_media_payload(
                                            mime_type=mime_type,
                                            origin="image_url",
                                            url=storage_info.get("url"),
                                            storage_info=storage_info
                                        )
                                    else:
                                        # Fallback to data URL if upload failed
                                        media_entry = _register_media_payload(
                                            mime_type=mime_type,
                                            origin="image_url",
                                            data_url=url_value
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to parse data URL: {e}")
                                    mime_type = part.get("mime_type") or "image/*"
                                    media_entry = _register_media_payload(
                                        mime_type=mime_type,
                                        origin="image_url",
                                        data_url=url_value
                                    )
                            else:
                                # Regular HTTP(S) URL, use directly
                                mime_type = part.get("mime_type") or "image/*"
                                media_entry = _register_media_payload(
                                    mime_type=mime_type,
                                    origin="image_url",
                                    url=url_value
                                )
                            
                            chunk_media.append(media_entry)
                            placeholder = _media_markdown(media_entry)
                            if placeholder:
                                text_segments.append(placeholder)

                    file_data = part.get("file_data") or part.get("fileData")
                    if file_data:
                        await _walk(file_data)
                    return

                text_attr = getattr(part, "text", None)
                if text_attr:
                    text_segments.append(text_attr)
                inline_attr = getattr(part, "inline_data", None)
                if inline_attr:
                    await _walk({"inline_data": {"mime_type": getattr(inline_attr, "mime_type", None), "data": getattr(inline_attr, "data", None)}})
                content_attr = getattr(part, "content", None)
                if content_attr:
                    await _walk(content_attr)

            await _walk(content_part)
            return "".join(text_segments), chunk_media

        cache = get_cache_service()
        try:
            async for chunk in client.astream(lc_messages):
                # Check for stop signal
                if conversation_id and await cache.exists(f"stop_signal:{conversation_id}"):
                    await cache.delete(f"stop_signal:{conversation_id}")
                    break

                # Log chunk structure for debugging
                if self.google_adapter.is_google_provider(assistant):
                    logger.debug(f"Gemini chunk attributes: {dir(chunk)}")
                    logger.debug(f"Gemini chunk.response_metadata: {getattr(chunk, 'response_metadata', {})}")
                    logger.debug(f"Gemini chunk.additional_kwargs: {getattr(chunk, 'additional_kwargs', {})}")
                
                # Collect full response parts for Gemini multi-turn editing
                if self.google_adapter.is_google_provider(assistant) and hasattr(chunk, 'content'):
                    logger.debug(f"Gemini chunk content type: {type(chunk.content)}")
                    
                    if isinstance(chunk.content, list):
                        # Content is already structured parts
                        logger.debug(f"Processing {len(chunk.content)} parts from chunk")
                        for idx, part in enumerate(chunk.content):
                            logger.debug(f"  Part {idx} type: {type(part)}, has thought_signature: {hasattr(part, 'thought_signature')}")
                            part_dict = self.google_adapter.serialize_part(part)
                            if part_dict:
                                logger.debug(f"  Serialized part {idx}: keys={list(part_dict.keys())}")
                                full_response_parts.append(part_dict)
                    elif hasattr(chunk.content, '__dict__'):
                        # Single part object
                        logger.debug(f"Single part object: {type(chunk.content)}")
                        part_dict = self.google_adapter.serialize_part(chunk.content)
                        if part_dict:
                            logger.debug(f"Serialized single part: keys={list(part_dict.keys())}")
                            full_response_parts.append(part_dict)
                    elif chunk.content:  # string
                        # Plain text chunk
                        logger.debug(f"Plain text chunk: {len(chunk.content)} chars")
                        full_response_parts.append({"type": "text", "text": chunk.content})
                
                # Extract token usage metadata
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    usage = chunk.usage_metadata
                    if isinstance(usage, dict):
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)
                        
                        if total_tokens > 0:
                            token_usage["input_tokens"] = input_tokens
                            token_usage["output_tokens"] = output_tokens
                            token_usage["total_tokens"] = total_tokens
                
                # Yield content chunks
                if hasattr(chunk, "content") and chunk.content:
                    content_text, chunk_media = await _extract_content_and_media(chunk.content)
                    if not content_text and not chunk_media:
                        continue

                    event_payload = {
                        "type": "content_chunk",
                        "data": {
                            "content": content_text,
                            "is_final": False
                        }
                    }
                    if chunk_media:
                        event_payload["data"]["media"] = chunk_media
                    yield event_payload
            
            # Send final chunk
            yield {
                "type": "content_chunk",
                "data": {
                    "content": "",
                    "is_final": True
                }
            }
            
            # Send token usage if available
            if token_usage["total_tokens"] > 0:
                yield {
                    "type": "token_usage",
                    "data": token_usage
                }
            
            # Send full response parts for Gemini (for multi-turn image editing)
            if full_response_parts:
                yield {
                    "type": "full_response_parts",
                    "data": {"parts": full_response_parts}
                }
                logger.info(f"Collected {len(full_response_parts)} parts for Gemini multi-turn editing")
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise ValueError(f"AI model error: {str(e)}")
    
    async def generate_conversation_title(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        auto_update: bool = True
    ) -> tuple[str, str, bool]:
        """
        Generate conversation title
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            auto_update: Whether to automatically update title to database
            
        Returns:
            tuple[str, str, bool]: (Generated title, Model name used, Whether updated to database)
        """
        conversation = await self.conversation_service.get_conversation_with_model(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        # Get system configured title generation model ID
        title_model_id = await config_service.get_title_generation_model_id(self.session)
        
        # Determine which model to use
        if title_model_id:
            # Use configured dedicated model
            title_model_result = await self.session.execute(
                select(Model)
                .options(selectinload(Model.provider))
                .where(
                    and_(
                        Model.id == uuid.UUID(title_model_id),
                        Model.status == "ACTIVE"
                    )
                )
            )
            title_model = title_model_result.scalar_one_or_none()
            
            if not title_model:
                # If configured model doesn't exist or unavailable, fallback to conversation's assistant model
                title_model = conversation.assistant.model
        else:
            # Use conversation's assistant model
            title_model = conversation.assistant.model

        logger.debug(
            f"Generating title for conversation {conversation_id} using model {title_model.name} "
            f"(configured model ID: {title_model_id})"
        )
        
        # Get first user message content as context
        messages_result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.message_type == MessageTypeEnum.USER
                )
            )
            .order_by(Message.created_at.asc())
            .limit(1)  # Get first user message
        )
        messages = messages_result.scalars().all()
        
        if not messages:
            raise ValueError("No messages found in conversation")
        
        # Use first user message as context
        first_user_message = messages[0]
        
        # Build AI request
        instruction = (
            "You are a conversation title generator. Generate a concise title (3-15 words) for the conversation below.\n"
            "Requirements:\n"
            "1. The title MUST be in the same language as the conversation content.\n"
            "2. Do NOT include any prefixes (e.g. 'Title:', 'Language:'), labels, or quotation marks.\n"
            "3. Return ONLY the raw title text."
        )
        combined_user_content = (
            f"{instruction}\n\n"
            + "--- Conversation starts below ---\n"
            + first_user_message.content
        )
        chat_messages = [
            ChatMessage(role=MessageRole.USER, content=combined_user_content)
        ]
        
        # Create LangChain client
        try:
            client = create_chat_model(
                provider=title_model.provider,
                model_name=title_model.name,
                temperature=0.3,  # Lower temperature for stable title generation
                max_tokens=50     # Titles don't need to be too long
            )
        except Exception as e:
            raise ValueError(f"Failed to create client: {str(e)}")
        
        # Convert to LangChain messages
        lc_messages = [msg.to_langchain_message() for msg in chat_messages]
        
        try:
            # Call AI to generate title
            response = await client.ainvoke(lc_messages)
            title = response.content.strip()
            
            # Auto-update conversation title to database if needed
            updated = False
            if auto_update:
                try:
                    conversation.title = title
                    await self.session.commit()
                    updated = True
                except Exception:
                    # If update fails, don't affect title generation result
                    await self.session.rollback()
                    updated = False
            
            return title, title_model.name, updated
            
        except Exception as e:
            raise ValueError(f"Failed to generate title: {str(e)}")
    
    
    async def delete_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        return await self.conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    async def hard_delete_conversation(
        self,
        conversation_id: uuid.UUID
    ) -> bool:
        """Permanently delete a conversation."""
        return await self.conversation_service.hard_delete_conversation(
            conversation_id=conversation_id
        )
    
    async def archive_conversation(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        return await self.conversation_service.archive_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
        )