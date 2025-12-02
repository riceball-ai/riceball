"""Prompt builder utilities for LangchainChatService."""
from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.assistants.models import Assistant, Conversation, Message, MessageTypeEnum
from src.rag.service import RAGService
from src.files.storage import storage_service

from .models import ChatMessage, MessageRole
from .providers.google_adapter import GoogleProviderAdapter
from .token_utils import TokenCounter, get_default_token_counter

logger = logging.getLogger(__name__)

_DATA_URL_MARKDOWN_PATTERN = re.compile(r"!\[[^\]]*\]\(data:image/[^)]+\)", re.IGNORECASE)
_DATA_URL_INLINE_PATTERN = re.compile(r"data:image/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+", re.IGNORECASE)

RAG_INSTRUCTIONS = (
    "Here are reference materials from the knowledge base related to the user's question. Please follow these guidelines:\n"
    "1. Prioritize answering based on the reference materials and cite the reference number where appropriate.\n"
    "2. If the materials are insufficient to answer the question, please state so clearly.\n"
    "3. Answer in the user's language, ensuring accuracy, clarity, and structure.\n"
    "\nReference Materials:\n{context_text}"
)


class PromptBuilder:
    """Builds prompt messages with history, RAG context, and safety limits."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        google_adapter: Optional[GoogleProviderAdapter] = None,
    ) -> None:
        self.session = session
        self.google_adapter = google_adapter or GoogleProviderAdapter()

    def get_system_prompt(self, assistant: Assistant, language: Optional[str] = None) -> str:
        """Get translated system prompt based on language."""
        # Determine language context
        user_lang = language or "en"
        
        # Normalize language code (e.g., zh-CN -> zh)
        lang_code = user_lang.split("-")[0].lower() if user_lang else "en"

        # Get translated system prompt if available
        system_prompt = assistant.system_prompt or "You are a helpful AI agent."
        
        if assistant.translations:
            translations = assistant.translations
            
            # Try exact match first, then language code match
            if user_lang in translations and "system_prompt" in translations[user_lang]:
                system_prompt = translations[user_lang]["system_prompt"]
            elif lang_code in translations and "system_prompt" in translations[lang_code]:
                system_prompt = translations[lang_code]["system_prompt"]
        
        return system_prompt

    async def build_prompt_messages(
        self,
        conversation: Conversation,
        user_input: str,
        *,
        exclude_message_ids: Optional[List[uuid.UUID]] = None,
        current_images: Optional[List[Dict[str, Any]]] = None,
        language: Optional[str] = None,
    ) -> List[ChatMessage]:
        token_counter = get_default_token_counter()
        model = conversation.assistant.model
        max_context_tokens = model.max_context_tokens or 4096
        max_output_tokens = model.max_output_tokens or 1024

        available_input_tokens = max_context_tokens - max_output_tokens
        safety_ratio = 0.9
        safe_input_tokens = int(available_input_tokens * safety_ratio)

        logger.info(
            "Token budget for conversation %s: max_context=%s, max_output=%s, available_input=%s, safe_input=%s",
            conversation.id,
            max_context_tokens,
            max_output_tokens,
            available_input_tokens,
            safe_input_tokens,
        )

        fixed_messages: List[ChatMessage] = []
        system_parts: List[str] = []

        # Determine language context
        user_lang = language or "en"
        if not language and conversation.user and conversation.user.language:
            user_lang = conversation.user.language
        
        # Normalize language code (e.g., zh-CN -> zh)
        lang_code = user_lang.split("-")[0].lower() if user_lang else "en"

        logger.info(
            "Building prompt for conversation %s. User lang: %s, Normalized: %s",
            conversation.id,
            user_lang,
            lang_code
        )

        # Get translated system prompt if available
        system_prompt = conversation.assistant.system_prompt
        if conversation.assistant.translations:
            translations = conversation.assistant.translations
            logger.debug("Assistant translations available: %s", list(translations.keys()))
            
            # Try exact match first, then language code match
            if user_lang in translations and "system_prompt" in translations[user_lang]:
                system_prompt = translations[user_lang]["system_prompt"]
                logger.info("Using exact match translation for system prompt (%s)", user_lang)
            elif lang_code in translations and "system_prompt" in translations[lang_code]:
                system_prompt = translations[lang_code]["system_prompt"]
                logger.info("Using language code match translation for system prompt (%s)", lang_code)
            else:
                logger.info("No matching translation found for system prompt, using default")
        if system_prompt:
            system_parts.append(system_prompt)

        if not conversation.assistant.enable_agent:
            rag_context = await self._get_rag_context_content(
                conversation.assistant, 
                user_input,
                language=lang_code
            )
            if rag_context:
                system_parts.append(rag_context)
        else:
            logger.info(
                "Agent mode enabled - skipping automatic RAG context injection for conversation %s",
                conversation.id,
            )

        if system_parts:
            combined_system_content = "\n\n".join(system_parts)
            fixed_messages.append(
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content=combined_system_content,
                )
            )

        if current_images:
            inline_only = self._requires_inline_images(conversation.assistant)
            content_parts: List[Dict[str, Any]] = []
            if user_input:
                content_parts.append({"type": "text", "text": user_input})

            for img in current_images:
                image_part = await self._build_image_part(img, inline_only=inline_only)
                if image_part:
                    content_parts.append(image_part)

            if content_parts:
                current_user_message = ChatMessage(role=MessageRole.USER, content=content_parts)
                logger.info(
                    "Created multimodal user message with %s images for conversation %s",
                    len(current_images),
                    conversation.id,
                )
            else:
                current_user_message = ChatMessage(role=MessageRole.USER, content=user_input)
        else:
            current_user_message = ChatMessage(role=MessageRole.USER, content=user_input)
        fixed_messages.append(current_user_message)

        fixed_tokens = token_counter.count_messages_tokens(fixed_messages)
        if fixed_tokens > safe_input_tokens:
            raise ValueError(
                "Input too long: fixed messages use %s tokens, which exceeds the safe limit of %s tokens. "
                "Please reduce the length of your message or system prompt." % (fixed_tokens, safe_input_tokens)
            )

        available_history_tokens = safe_input_tokens - fixed_tokens
        logger.info(
            "Fixed messages use %s tokens, available for history: %s tokens",
            fixed_tokens,
            available_history_tokens,
        )

        history_messages = await self._get_conversation_history_with_token_limit(
            conversation,
            available_history_tokens,
            token_counter,
            exclude_message_ids,
        )

        final_messages: List[ChatMessage] = []
        if system_parts:
            final_messages.append(fixed_messages[0])
        final_messages.extend(history_messages)
        final_messages.append(current_user_message)

        final_messages = self.google_adapter.normalize_messages_for_gemini(
            final_messages,
            conversation.assistant,
        )

        total_tokens = 0
        for msg in final_messages:
            if isinstance(msg.content, str):
                total_tokens += token_counter.count_message_tokens(msg)
            else:
                text_parts: List[str] = []
                if isinstance(msg.content, list):
                    for part in msg.content:
                        if isinstance(part, dict) and part.get("text"):
                            text_parts.append(part["text"])
                temp_msg = ChatMessage(role=msg.role, content=" ".join(text_parts) if text_parts else "")
                total_tokens += token_counter.count_message_tokens(temp_msg)

        logger.info(
            "Final prompt for conversation %s: %s messages, %s total tokens (%s/%s budget used)",
            conversation.id,
            len(final_messages),
            total_tokens,
            total_tokens,
            safe_input_tokens,
        )

        logger.debug("Final message sequence for conversation %s:", conversation.id)
        for idx, msg in enumerate(final_messages):
            if isinstance(msg.content, str):
                preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
            else:
                preview = f"<multi-modal content with {len(msg.content)} parts>"
            logger.debug("  %s: %s - %s", idx, msg.role.value, preview)

        return final_messages

    async def _get_conversation_history_with_token_limit(
        self,
        conversation: Conversation,
        token_limit: int,
        token_counter: TokenCounter,
        exclude_message_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[ChatMessage]:
        if token_limit <= 0:
            logger.info("No tokens available for history messages (limit: %s)", token_limit)
            return []

        max_message_count = conversation.assistant.max_history_messages
        if max_message_count is not None and max_message_count <= 0:
            logger.info(
                "Assistant configured to include no history messages (max_history_messages: %s)",
                max_message_count,
            )
            return []

        query = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        )
        if exclude_message_ids:
            query = query.where(~Message.id.in_(exclude_message_ids))

        result = await self.session.execute(query)
        all_messages = result.scalars().all()

        logger.debug("📚 Fetched %s total messages from database", len(all_messages))
        for idx, msg in enumerate(all_messages):
            extra = msg.extra_data or {}
            has_gemini_parts = bool(
                extra.get("gemini_response_parts")
                or extra.get("gemini_response_parts_ref")
            )
            logger.debug(
                "  Message %s: role=%s, created_at=%s, has_gemini_parts=%s",
                idx,
                msg.message_type.value,
                msg.created_at,
                has_gemini_parts,
            )

        valid_messages = [
            msg
            for msg in all_messages
            if (msg.content and msg.content.strip())
            or (
                msg.extra_data
                and (
                    msg.extra_data.get("gemini_response_parts")
                    or msg.extra_data.get("gemini_response_parts_ref")
                )
            )
        ]
        logger.debug("📝 After filtering empty: %s valid messages", len(valid_messages))

        corrected_messages: List[Message] = []
        i = 0
        while i < len(valid_messages):
            current_msg = valid_messages[i]
            if (
                i + 1 < len(valid_messages)
                and valid_messages[i + 1].created_at == current_msg.created_at
            ):
                next_msg = valid_messages[i + 1]
                if (
                    current_msg.message_type == MessageTypeEnum.ASSISTANT
                    and next_msg.message_type == MessageTypeEnum.USER
                ):
                    corrected_messages.append(next_msg)
                    corrected_messages.append(current_msg)
                    i += 2
                    continue
            corrected_messages.append(current_msg)
            i += 1

        if max_message_count is not None and max_message_count > 0:
            if len(corrected_messages) > max_message_count:
                corrected_messages = corrected_messages[-max_message_count:]

        selected_messages: List[ChatMessage] = []
        current_tokens = 0
        for msg in reversed(corrected_messages):
            role = (
                MessageRole.USER
                if msg.message_type == MessageTypeEnum.USER
                else MessageRole.ASSISTANT
            )

            should_use_multimodal = False
            parts: List[Any] = []
            if (
                role == MessageRole.ASSISTANT
                and self.google_adapter.is_google_provider(conversation.assistant)
                and msg.extra_data
            ):
                parts_payload = (
                    msg.extra_data.get("gemini_response_parts_ref")
                    or msg.extra_data.get("gemini_response_parts")
                )
                if parts_payload:
                    parts = await self._rehydrate_gemini_parts(parts_payload)
                    for part in parts:
                        if not isinstance(part, dict):
                            continue
                        inline_blob = part.get("inline_data") or part.get("inlineData")
                        image_payload = part.get("image_url") or part.get("imageUrl")
                        signature_payload = (
                            part.get("thought_signature")
                            or (part.get("extras") or {}).get("signature")
                        )
                        if inline_blob or image_payload or signature_payload:
                            should_use_multimodal = True
                            break
            elif role == MessageRole.USER and msg.extra_data:
                images_payload = msg.extra_data.get("images")
                if images_payload:
                    inline_only = self._requires_inline_images(conversation.assistant)
                    for image in images_payload:
                        image_part = await self._build_image_part(image, inline_only=inline_only)
                        if image_part:
                            if not should_use_multimodal:
                                parts = []
                                should_use_multimodal = True
                            parts.append(image_part)

            if should_use_multimodal:
                content_parts: List[Any] = []
                if role == MessageRole.USER and msg.content and msg.content.strip():
                    content_parts.append({"type": "text", "text": msg.content.strip()})
                content_parts.extend(parts)
                chat_message = ChatMessage(role=role, content=content_parts)
                logger.debug(
                    "Restored multimodal message with %s parts (role=%s)",
                    len(content_parts),
                    role,
                )
                text_for_counting = (
                    msg.content.strip()
                    if msg.content and msg.content.strip()
                    else "[image]"
                )
                sanitized = self._sanitize_content_for_prompt(text_for_counting)
                temp_message = ChatMessage(role=role, content=sanitized)
                message_tokens = token_counter.count_message_tokens(temp_message)
            else:
                if not msg.content or not msg.content.strip():
                    continue
                sanitized = self._sanitize_content_for_prompt(msg.content.strip())
                chat_message = ChatMessage(role=role, content=sanitized)
                message_tokens = token_counter.count_message_tokens(chat_message)

            if current_tokens + message_tokens > token_limit:
                logger.info(
                    "Token limit reached. Stopping at %s messages (current: %s, would be: %s, limit: %s)",
                    len(selected_messages),
                    current_tokens,
                    current_tokens + message_tokens,
                    token_limit,
                )
                break

            selected_messages.append(chat_message)
            current_tokens += message_tokens
            logger.debug(
                "Added message %s: %s tokens (total: %s/%s)",
                len(selected_messages),
                message_tokens,
                current_tokens,
                token_limit,
            )

        final_messages = list(reversed(selected_messages))
        logger.info(
            "Selected %s history messages using %s/%s tokens",
            len(final_messages),
            current_tokens,
            token_limit,
        )
        return final_messages

    async def _rehydrate_gemini_parts(
        self,
        payload: Any,
    ) -> List[Any]:
        """Restore Gemini parts from inline list or S3 reference."""
        if payload is None:
            return []

        if isinstance(payload, list):
            raw_parts = payload
        elif isinstance(payload, dict):
            raw_parts = await self._load_gemini_parts_from_storage(payload)
        else:
            logger.warning("Unknown Gemini parts payload type: %s", type(payload))
            return []

        if not raw_parts:
            return []

        return await self._rehydrate_parts_list(raw_parts)

    async def _rehydrate_parts_list(self, parts: List[Any]) -> List[Any]:
        cache: Dict[str, str] = {}

        async def _rehydrate_node(node: Any) -> Any:
            if isinstance(node, list):
                result_list = []
                for item in node:
                    result_list.append(await _rehydrate_node(item))
                return result_list
            if not isinstance(node, dict):
                return node

            updated: Dict[str, Any] = {}
            for key, value in node.items():
                if key in ("inline_data", "inlineData") and isinstance(value, dict):
                    updated["inline_data"] = await self._rehydrate_inline_data(value, cache)
                elif key in ("image_url", "imageUrl") and isinstance(value, dict):
                    updated["image_url"] = self._rehydrate_image_url(value)
                elif key == "parts" and isinstance(value, list):
                    updated["parts"] = []
                    for nested in value:
                        updated["parts"].append(await _rehydrate_node(nested))
                else:
                    updated[key] = value
            return updated

        rehydrated: List[Any] = []
        for part in parts:
            rehydrated.append(await _rehydrate_node(part))
        return rehydrated

    def _requires_inline_images(self, assistant: Assistant) -> bool:
        """Determine if downstream provider expects inline image payloads."""
        return self.google_adapter.is_google_provider(assistant)

    async def _build_image_part(
        self,
        image: Dict[str, Any],
        *,
        inline_only: bool,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(image, dict):
            return None

        mime_value = (
            image.get("mime_type")
            or image.get("mimeType")
            or image.get("content_type")
            or image.get("contentType")
        )
        alt_text = image.get("alt")

        if inline_only:
            inline_url = await self._ensure_inline_data_url(image, fallback_mime=mime_value)
            if not inline_url:
                logger.warning("Unable to generate inline data for image, skipping this attachment")
                return None
            entry: Dict[str, Any] = {"type": "image_url", "image_url": {"url": inline_url}}
        else:
            source_url = image.get("url")
            if not source_url:
                file_key = self._resolve_file_key(image)
                if file_key:
                    try:
                        source_url = await storage_service.get_public_url(file_key)
                    except Exception as exc:
                        logger.warning("Failed to get image URL (%s): %s", file_key, exc)
                        source_url = None
            if not source_url:
                inline_url = image.get("data_url") or image.get("dataUrl")
                if inline_url:
                    source_url = inline_url
            if not source_url:
                logger.warning("Image missing available URL, skipping this attachment")
                return None
            entry = {"type": "image_url", "image_url": {"url": source_url}}

        if inline_only:
            if mime_value:
                entry["mime_type"] = mime_value
            if alt_text:
                entry["alt"] = alt_text
        return entry

    async def _ensure_inline_data_url(
        self,
        image: Dict[str, Any],
        *,
        fallback_mime: Optional[str] = None,
    ) -> Optional[str]:
        existing = image.get("data_url") or image.get("dataUrl")
        if existing and existing.startswith("data:"):
            return existing

        source_url = image.get("url")
        if source_url and source_url.startswith("data:"):
            return source_url

        file_key = self._resolve_file_key(image)
        if not file_key:
            logger.warning("Unable to locate image file, cannot convert to base64")
            return None

        try:
            file_obj, content_type = await storage_service.download_file(file_key)
        except Exception as exc:
            logger.warning("Failed to download image (%s): %s", file_key, exc)
            return None

        data = file_obj.getvalue()
        mime_type = fallback_mime or content_type or "application/octet-stream"
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _resolve_file_key(self, image: Dict[str, Any]) -> Optional[str]:
        direct_key = (
            image.get("file_key")
            or image.get("fileKey")
            or image.get("file_path")
            or image.get("filePath")
        )
        if direct_key:
            return direct_key

        url = image.get("url")
        if not url:
            return None

        candidates = [storage_service.external_endpoint_url, storage_service.endpoint_url]
        for base in candidates:
            if not base:
                continue
            normalized = base.rstrip("/") + "/"
            if url.startswith(normalized):
                return url[len(normalized) :]

        parsed = urlparse(url)
        return parsed.path.lstrip("/") or None

    async def _load_gemini_parts_from_storage(
        self,
        reference: Dict[str, Any],
    ) -> List[Any]:
        file_key = reference.get("file_key")
        if not file_key:
            logger.warning("Gemini parts reference missing file_key")
            return []

        try:
            file_obj, _ = await storage_service.download_file(file_key)
        except Exception as exc:
            logger.warning("Failed to download Gemini parts file %s: %s", file_key, exc)
            return []

        raw_bytes = file_obj.getvalue()
        if not raw_bytes:
            logger.warning("Gemini parts file is empty: %s", file_key)
            return []

        try:
            decoded = raw_bytes.decode("utf-8")
            payload = json.loads(decoded)
        except Exception as exc:
            logger.warning("Failed to parse Gemini parts JSON (%s): %s", file_key, exc)
            return []

        if isinstance(payload, list):
            return payload

        logger.warning("Gemini parts JSON is not a list (%s)", file_key)
        return []

    async def _rehydrate_inline_data(
        self,
        inline_payload: Dict[str, Any],
        cache: Dict[str, str],
    ) -> Dict[str, Any]:
        result = dict(inline_payload)
        if result.get("data"):
            return result

        storage_meta = inline_payload.get("storage") or {}
        file_key = storage_meta.get("file_key")
        if not file_key:
            logger.debug("inline_data missing storage.file_key, skipping backfill")
            return result

        cache_key = inline_payload.get("data_hash") or file_key
        if cache_key in cache:
            result["data"] = cache[cache_key]
            return result

        try:
            file_obj, content_type = await storage_service.download_file(file_key)
        except Exception as exc:
            logger.warning("Failed to download S3 media %s: %s", file_key, exc)
            return result

        binary = file_obj.getvalue()
        if not binary:
            logger.warning("S3 media is empty: %s", file_key)
            return result

        encoded = base64.b64encode(binary).decode("utf-8")
        result["data"] = encoded
        if cache_key:
            cache[cache_key] = encoded

        if not result.get("mime_type"):
            result["mime_type"] = (
                inline_payload.get("mime_type")
                or storage_meta.get("content_type")
                or storage_meta.get("mime_type")
                or content_type
                or "application/octet-stream"
            )

        return result

    def _rehydrate_image_url(self, image_payload: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(image_payload)
        if result.get("url"):
            return result
        storage_meta = image_payload.get("storage") or {}
        storage_url = storage_meta.get("url")
        if storage_url:
            result["url"] = storage_url
        return result

    async def _get_rag_context_content(
        self,
        assistant: Assistant,
        user_query: str,
        language: str = "zh",
    ) -> Optional[str]:
        knowledge_base_ids = getattr(assistant, "knowledge_base_ids", None) or []
        if not knowledge_base_ids:
            return None

        rag_config = getattr(assistant, "rag_config", {}) or {}
        retrieval_count = rag_config.get("retrieval_count") or 5

        rag_service = RAGService(self.session)
        context_entries: List[str] = []
        entry_index = 1

        for raw_kb_id in knowledge_base_ids:
            try:
                kb_uuid = raw_kb_id if isinstance(raw_kb_id, uuid.UUID) else uuid.UUID(str(raw_kb_id))
            except Exception:
                logger.warning(
                    "Invalid knowledge base ID '%s' configured on assistant %s",
                    raw_kb_id,
                    assistant.id,
                )
                continue

            try:
                relevance_docs = await rag_service.relevance_search(
                    query=user_query,
                    knowledge_base_id=kb_uuid,
                    k=retrieval_count,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to retrieve RAG context for assistant %s (KB %s): %s",
                    assistant.id,
                    kb_uuid,
                    exc,
                )
                continue

            for doc in relevance_docs:
                metadata = doc.metadata or {}
                title = metadata.get("title", "Untitled Document")
                content = doc.page_content or ""
                context_entries.append(
                    f"[Reference {entry_index}] (Document {title})\n{content}"
                )
                entry_index += 1

        if not context_entries:
            return None

        context_text = "\n\n".join(context_entries)
        
        instructions = RAG_INSTRUCTIONS.format(context_text=context_text)
        return instructions

    @staticmethod
    def _sanitize_content_for_prompt(content: Optional[str]) -> str:
        if not content:
            return ""
        if not isinstance(content, str):
            logger.debug(
                "_sanitize_content_for_prompt received non-string content of type %s",
                type(content),
            )
            try:
                content = str(content)
            except Exception:
                return ""

        try:
            sanitized = _DATA_URL_MARKDOWN_PATTERN.sub("[Image content omitted]", content)
            sanitized = _DATA_URL_INLINE_PATTERN.sub("[Image data omitted]", sanitized)
        except TypeError as exc:
            logger.warning("Unable to sanitize message content (type=%s): %s", type(content), exc)
            return content

        return sanitized