"""Google/Gemini specific helpers for chat service."""
from __future__ import annotations

import ast
import base64
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from google.genai import types as genai_types

from src.assistants.models import Assistant

from ..models import ChatMessage, MessageRole

logger = logging.getLogger(__name__)


class GoogleProviderAdapter:
    """Encapsulates Gemini-specific normalization logic."""

    _MODALITY_NAME_MAP = {
        "UNSPECIFIED": "UNSPECIFIED",
        "TEXT": "TEXT",
        "AUDIO": "AUDIO",
        "IMAGE": "IMAGE",
        "VIDEO": "VIDEO",
    }
    _MODALITY_INT_MAP = {
        0: "UNSPECIFIED",
        1: "TEXT",
        2: "AUDIO",
        3: "IMAGE",
        4: "VIDEO",
    }
    _BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/=]+$")

    def build_contents_payload(
        self,
        messages: List[ChatMessage],
        assistant: Assistant,
    ) -> Tuple[List[genai_types.Content], Optional[str]]:
        """Convert internal ChatMessages to google-genai Content payload."""

        contents: List[genai_types.Content] = []
        system_parts: List[str] = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                text_value = self._stringify_content(msg.content)
                if text_value:
                    system_parts.append(text_value)
                continue

            if (
                msg.role == MessageRole.ASSISTANT
                and (
                    self._is_placeholder_message(msg)
                    or not isinstance(msg.content, list)
                )
            ):
                placeholder_text = self._stringify_content(msg.content)
                if placeholder_text:
                    system_parts.append(placeholder_text)
                continue

            parts = list(self._convert_content_to_parts(msg.content))
            if not parts:
                continue

            if msg.role == MessageRole.USER:
                contents.append(genai_types.UserContent(parts=parts))
            elif msg.role == MessageRole.ASSISTANT:
                contents.append(genai_types.ModelContent(parts=parts))
            else:
                logger.debug("Skipping unsupported role %s", msg.role)

        system_instruction = "\n\n".join(system_parts) if system_parts else None
        if system_instruction:
            logger.debug("Prepared system instruction with %s fragments", len(system_parts))
        return contents, system_instruction

    def build_generation_config(
        self,
        assistant: Assistant,
        overrides: Optional[Dict[str, Any]] = None,
        *,
        system_instruction: Optional[str] = None,
    ) -> genai_types.GenerateContentConfig:
        """Merge generation params into google-genai config object."""

        model_config = getattr(assistant.model, "generation_config", None) or {}
        assistant_overrides = (assistant.config or {}).get("additional_params", {}) or {}

        merged: Dict[str, Any] = {}
        for params in (model_config, assistant_overrides, overrides):
            if not params:
                continue
            for key, value in params.items():
                if value is None:
                    continue
                merged[key] = value

        normalized = self.normalize_generation_params(merged, assistant)
        if system_instruction:
            normalized["system_instruction"] = system_instruction

        try:
            return genai_types.GenerateContentConfig(**normalized)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Invalid Google generation config %s", exc)
            return genai_types.GenerateContentConfig(system_instruction=system_instruction)

    def is_google_provider(self, assistant: Assistant | None) -> bool:
        if not assistant:
            return False
        model = getattr(assistant, "model", None)
        provider = getattr(model, "provider", None)
        interface_type = (getattr(provider, "interface_type", "") or "").upper()
        return interface_type == "GOOGLE"

    def normalize_generation_params(
        self,
        params: Optional[Dict[str, Any]],
        assistant: Assistant,
    ) -> Dict[str, Any]:
        if not params:
            return {}
        normalized = dict(params)

        modalities_key = None
        for candidate in ("response_modalities", "responseModalities"):
            if candidate in normalized:
                modalities_key = candidate
                break
        if modalities_key:
            raw_modalities = normalized.pop(modalities_key)
            raw_values = self._ensure_list(raw_modalities)
            coerced_values: List[str] = []
            for item in raw_values:
                mapped = self._map_response_modality(item)
                if mapped is None:
                    logger.warning(
                        "Invalid response modality '%s' for Google model %s",
                        item,
                        getattr(getattr(assistant, "model", None), "name", "unknown"),
                    )
                    continue
                coerced_values.append(mapped)
            if coerced_values:
                normalized["response_modalities"] = coerced_values
            else:
                logger.warning(
                    "Removed response_modalities from Google model %s due to invalid values",
                    getattr(getattr(assistant, "model", None), "name", "unknown"),
                )

        image_config_key = None
        for candidate in ("image_config", "imageConfig"):
            if candidate in normalized:
                image_config_key = candidate
                break
        if image_config_key:
            image_config_payload = normalized.pop(image_config_key)
            existing_model_kwargs = normalized.get("model_kwargs")
            if existing_model_kwargs and not isinstance(existing_model_kwargs, dict):
                logger.warning(
                    "model_kwargs on Google model %s is not a dict. Overwriting with image_config",
                    getattr(getattr(assistant, "model", None), "name", "unknown"),
                )
                existing_model_kwargs = {}
            model_kwargs = existing_model_kwargs or {}
            model_kwargs["image_config"] = image_config_payload
            normalized["model_kwargs"] = model_kwargs
        return normalized

    def normalize_messages_for_gemini(
        self,
        messages: List[ChatMessage],
        assistant: Assistant,
    ) -> List[ChatMessage]:
        if not self.is_google_provider(assistant):
            return messages

        normalized: List[ChatMessage] = []
        placeholder_count = 0

        for msg in messages:
            if msg.role != MessageRole.ASSISTANT:
                normalized.append(msg)
                continue

            if isinstance(msg.content, list):
                normalized.append(msg)
                continue

            text_value = self._stringify_content(msg.content)
            if text_value:
                if isinstance(msg.content, str) and msg.content.strip() == text_value:
                    normalized.append(msg)
                else:
                    normalized.append(
                        ChatMessage(
                            role=MessageRole.ASSISTANT,
                            content=text_value,
                            metadata=msg.metadata,
                        )
                    )
                continue

            placeholder_count += 1
            placeholder_text = (
                f"[Gemini Note] Historical assistant response #{placeholder_count} lacks serializable content, "
                "placeholder description used to preserve context."
            )
            metadata = dict(msg.metadata or {})
            metadata["gemini_placeholder"] = True
            normalized.append(
                ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=placeholder_text,
                    metadata=metadata,
                )
            )
            logger.debug(
                "Inserted placeholder for empty Gemini assistant message #%s", placeholder_count
            )

        if placeholder_count:
            logger.info(
                "Gemini normalization replaced %s assistant messages with placeholders",
                placeholder_count,
            )

        return normalized

    def serialize_part(self, part: Any) -> Optional[Dict[str, Any]]:
        if part is None:
            return None

        result: Dict[str, Any] = {}
        text_content = None
        if hasattr(part, "text") and part.text:
            text_content = part.text
        elif isinstance(part, dict) and part.get("text"):
            text_content = part["text"]

        thought_sig = None
        if hasattr(part, "thought_signature") and part.thought_signature:
            thought_sig = part.thought_signature
        elif isinstance(part, dict) and part.get("thought_signature"):
            thought_sig = part["thought_signature"]

        if text_content:
            result["type"] = "text"
            result["text"] = text_content
            if thought_sig:
                result["extras"] = {
                    "signature": self._encode_signature(thought_sig)
                }

        inline_data = None
        if hasattr(part, "inline_data") and part.inline_data:
            inline = part.inline_data
            mime_type = getattr(inline, "mime_type", None) or getattr(inline, "mimeType", None)
            data = getattr(inline, "data", None)
            if mime_type and data:
                encoded_data = self._ensure_base64_data(data)
                if encoded_data:
                    inline_data = {"mime_type": mime_type, "data": encoded_data}
        elif isinstance(part, dict) and (part.get("inline_data") or part.get("inlineData")):
            inline = part.get("inline_data") or part.get("inlineData")
            mime_type = inline.get("mime_type") or inline.get("mimeType")
            data = inline.get("data")
            if mime_type and data:
                encoded_data = self._ensure_base64_data(data)
                if encoded_data:
                    inline_data = {"mime_type": mime_type, "data": encoded_data}

        if inline_data:
            result["inline_data"] = inline_data
            if not text_content:
                result["type"] = "image_url"
                result["image_url"] = {
                    "url": f"data:{inline_data['mime_type']};base64,{inline_data['data']}"
                }
                result["mime_type"] = inline_data["mime_type"]
            if thought_sig:
                existing_extras = result.get("extras", {})
                existing_extras["signature"] = self._encode_signature(thought_sig)
                result["extras"] = existing_extras

        return result if result else None

    def prepare_parts_for_storage(
        self,
        parts: Optional[List[Dict[str, Any]]],
        inline_storage_map: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Strip oversized inline payloads while recording storage references."""
        if not parts:
            return []

        storage_map = inline_storage_map or {}
        sanitized: List[Dict[str, Any]] = []
        for part in parts:
            sanitized.append(self._sanitize_part_for_storage(part, storage_map))
        return sanitized

    def _convert_content_to_parts(self, content: Any) -> Iterable[genai_types.Part]:
        if content is None:
            return []
        if isinstance(content, str):
            return [genai_types.Part.from_text(text=content)]
        if isinstance(content, list):
            parts: List[genai_types.Part] = []
            for item in content:
                part = self._convert_item_to_part(item)
                if part is not None:
                    parts.append(part)
            return parts
        return [genai_types.Part.from_text(text=str(content))]

    def _convert_item_to_part(self, item: Any) -> Optional[genai_types.Part]:
        if isinstance(item, str):
            return genai_types.Part.from_text(text=item)
        if not isinstance(item, dict):
            return None

        signature = self._decode_signature(item.get("extras", {}).get("signature"))

        if item.get("type") == "text":
            text = item.get("text")
            if text is None:
                return None
            part = genai_types.Part.from_text(text=text)
            if signature:
                part.thought_signature = signature
            return part

        if item.get("type") == "image_url":
            url = (item.get("image_url") or {}).get("url")
            mime_type = item.get("mime_type")
            return self._part_from_image_url(url, signature, mime_type)

        inline_data = item.get("inline_data") or item.get("inlineData")
        if inline_data:
            return self._part_from_inline_data(inline_data, signature)

        if item.get("parts"):
            parts: List[genai_types.Part] = []
            for nested in item["parts"]:
                nested_part = self._convert_item_to_part(nested)
                if nested_part:
                    parts.append(nested_part)
            if parts:
                return genai_types.Part(parts=parts)

        text_fallback = item.get("text") or item.get("content")
        if text_fallback:
            return genai_types.Part.from_text(text=text_fallback)

        return None

    def _sanitize_part_for_storage(
        self,
        part: Any,
        storage_map: Dict[str, Dict[str, Any]],
    ) -> Any:
        if isinstance(part, list):
            return [self._sanitize_part_for_storage(p, storage_map) for p in part]
        if not isinstance(part, dict):
            return part

        sanitized: Dict[str, Any] = {}
        for key, value in part.items():
            if key in ("inline_data", "inlineData") and isinstance(value, dict):
                sanitized["inline_data"] = self._sanitize_inline_payload(value, storage_map)
            elif key in ("image_url", "imageUrl") and isinstance(value, (dict, str)):
                sanitized["image_url"] = self._sanitize_image_payload(value, storage_map)
            elif key == "parts" and isinstance(value, list):
                sanitized["parts"] = [
                    self._sanitize_part_for_storage(item, storage_map)
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_inline_payload(
        self,
        inline_payload: Dict[str, Any],
        storage_map: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        mime_type = inline_payload.get("mime_type") or inline_payload.get("mimeType")
        if mime_type:
            sanitized["mime_type"] = mime_type

        data_hash = inline_payload.get("data_hash") or inline_payload.get("dataHash")
        storage_info = storage_map.get(data_hash) if data_hash else None
        if data_hash:
            sanitized["data_hash"] = data_hash
        if storage_info:
            sanitized["storage"] = self._compact_storage_metadata(storage_info)
        else:
            data_value = inline_payload.get("data")
            if data_value:
                sanitized["data"] = data_value

        for extra_key in ("extras", "thought_signature", "type"):
            if inline_payload.get(extra_key) is not None:
                sanitized[extra_key] = inline_payload[extra_key]

        return sanitized

    def _sanitize_image_payload(
        self,
        image_payload: Any,
        storage_map: Dict[str, Dict[str, Any]],
    ) -> Any:
        if isinstance(image_payload, str):
            return image_payload

        sanitized: Dict[str, Any] = {}
        data_hash = image_payload.get("data_hash") or image_payload.get("dataHash")
        storage_info = storage_map.get(data_hash) if data_hash else None

        if storage_info:
            sanitized["url"] = storage_info.get("url") or image_payload.get("url")
            sanitized["storage"] = self._compact_storage_metadata(storage_info)
        else:
            if image_payload.get("url"):
                sanitized["url"] = image_payload["url"]

        if data_hash:
            sanitized["data_hash"] = data_hash

        mime_type = image_payload.get("mime_type") or image_payload.get("mimeType")
        if mime_type:
            sanitized["mime_type"] = mime_type

        for extra_key in ("extras", "alt", "type"):
            if image_payload.get(extra_key) is not None:
                sanitized[extra_key] = image_payload[extra_key]

        return sanitized

    @staticmethod
    def _compact_storage_metadata(storage_info: Dict[str, Any]) -> Dict[str, Any]:
        allowed_keys = ("file_key", "url", "size", "content_type", "mime_type")
        return {
            key: storage_info.get(key)
            for key in allowed_keys
            if storage_info.get(key) is not None
        }

    def _part_from_inline_data(
        self,
        inline: Dict[str, Any],
        signature: Optional[bytes],
    ) -> Optional[genai_types.Part]:
        mime_type = inline.get("mime_type") or inline.get("mimeType")
        data = inline.get("data")
        if not mime_type or not data:
            return None
        try:
            if isinstance(data, str):
                normalized = self._normalize_base64_payload(data)
                if not normalized:
                    return None
                payload = base64.b64decode(normalized)
            else:
                payload = data
        except Exception:
            logger.warning("Invalid inline_data payload for Gemini request")
            return None
        blob = genai_types.Blob(mime_type=mime_type, data=payload)
        part = genai_types.Part(inline_data=blob)
        if signature:
            part.thought_signature = signature
        return part

    def _part_from_image_url(
        self,
        url: Optional[str],
        signature: Optional[bytes],
        mime_type: Optional[str],
    ) -> Optional[genai_types.Part]:
        if not url:
            return None
        if signature and not url.startswith("data:"):
            part = genai_types.Part(text="")
            part.thought_signature = signature
            return part
        if url.startswith("data:"):
            try:
                header, payload = url.split(",", 1)
            except ValueError:
                logger.warning("Malformed data URL for image input")
                return None
            mime = mime_type or header.split(":", 1)[1].split(";", 1)[0]
            normalized_payload = self._normalize_base64_payload(payload)
            if not normalized_payload:
                return None
            try:
                binary = base64.b64decode(normalized_payload)
            except Exception:
                logger.warning("Failed to decode data URL image")
                return None
            blob = genai_types.Blob(mime_type=mime, data=binary)
            part = genai_types.Part(inline_data=blob)
            if signature:
                part.thought_signature = signature
            return part

        part = genai_types.Part.from_uri(file_uri=url, mime_type=mime_type or "image/png")
        if signature:
            part.thought_signature = signature
        return part

    def _stringify_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            texts: List[str] = []
            for part in content:
                if isinstance(part, dict) and part.get("text"):
                    texts.append(part["text"])
            return "\n\n".join(texts).strip()
        return str(content).strip() if content else ""

    def _ensure_list(self, value: Any) -> List[Any]:
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    def _ensure_base64_data(self, data: Any) -> Optional[str]:
        if data is None:
            return None
        if isinstance(data, bytes):
            try:
                return base64.b64encode(data).decode("utf-8")
            except Exception:
                logger.warning("Failed to base64-encode inline_data bytes")
                return None
        if isinstance(data, str):
            return self._normalize_base64_payload(data)
        logger.warning("Unsupported inline_data payload type: %s", type(data))
        return None

    def _normalize_base64_payload(self, value: str) -> Optional[str]:
        if not value:
            return None
        cleaned = value.strip().replace("\n", "").replace("\r", "")
        if not cleaned:
            return None
        if cleaned.startswith("b'") and cleaned.endswith("'"):
            literal = cleaned
        elif cleaned.startswith('b"') and cleaned.endswith('"'):
            literal = cleaned
        else:
            literal = None

        if literal:
            try:
                evaluated = ast.literal_eval(literal)
                if isinstance(evaluated, bytes):
                    return base64.b64encode(evaluated).decode("ascii")
            except Exception:
                logger.warning("Failed to parse legacy bytes literal in Gemini payload")

        if not self._BASE64_PATTERN.fullmatch(cleaned):
            try:
                raw_bytes = cleaned.encode("latin-1", errors="ignore")
                if not raw_bytes:
                    return None
                return base64.b64encode(raw_bytes).decode("ascii")
            except Exception:
                logger.warning("Failed to normalize non-base64 Gemini payload")
                return None
        return cleaned

    def _is_placeholder_message(self, message: ChatMessage) -> bool:
        metadata = message.metadata or {}
        return bool(metadata.get("gemini_placeholder"))

    def _map_response_modality(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, int):
            return self._MODALITY_INT_MAP.get(value)
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized.startswith("RESPONSE_MODALITY_"):
                normalized = normalized.replace("RESPONSE_MODALITY_", "")
            if normalized.isdigit():
                return self._MODALITY_INT_MAP.get(int(normalized))
            return self._MODALITY_NAME_MAP.get(normalized)
        return None

    @staticmethod
    def _encode_signature(signature: Any) -> str:
        if isinstance(signature, bytes):
            return base64.b64encode(signature).decode("utf-8")
        if isinstance(signature, str):
            return signature
        logger.warning("Unsupported thought_signature type: %s", type(signature))
        return ""

    @staticmethod
    def _decode_signature(value: Optional[str]) -> Optional[bytes]:
        if not value:
            return None
        try:
            return base64.b64decode(value)
        except Exception:
            logger.warning("Failed to decode thought_signature payload")
            return None