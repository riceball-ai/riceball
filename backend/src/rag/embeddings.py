import uuid
import logging
import asyncio
from typing import List, Optional, Dict

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database import async_session_maker
from src.ai_models.models import Model, ModelProvider, PROVIDER_INTERFACE_TYPES

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Vector Embedding Service - Provides LangChain Embeddings instances based on model info"""

    def __init__(self):
        # Cache initialized embedders to avoid repeated construction
        self._embedder_cache: Dict[str, Embeddings] = {}

    async def get_embedder(self, model_id: str) -> Embeddings:
        """Get LangChain Embeddings instance by model ID"""
        model = await self._get_model_by_id(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        if "embedding" not in model.capabilities:
            raise ValueError(f"Model {model.name} does not support embedding")

        return await self._get_embedder_for_model(model)
    
    async def list_available_embedding_models(self) -> List[dict]:
        """Get all available embedding models"""
        try:
            async with async_session_maker() as session:
                
                stmt = select(Model).options(
                    selectinload(Model.provider)
                ).where(
                    Model.status == "ACTIVE"
                )
                result = await session.execute(stmt)
                all_models = result.scalars().all()
                
                # Filter models with embedding capability at Python level for database compatibility
                models = [m for m in all_models if "embedding" in m.capabilities]
                
                return [
                    {
                        "id": str(model.id),
                        "name": model.name,
                        "display_name": model.display_name,
                        "provider": model.provider.display_name if model.provider else "Unknown",
                        "description": model.description,
                        "max_context_tokens": model.max_context_tokens
                    }
                    for model in models
                ]
                
        except Exception as e:
            logger.error(f"Failed to list embedding models: {e}")
            return []
    
    async def _get_model_by_id(self, model_id: str) -> Optional[Model]:
        """Get model by ID"""
        try:
            async with async_session_maker() as session:
                
                stmt = select(Model).options(
                    selectinload(Model.provider)
                ).where(Model.id == uuid.UUID(model_id))
                result = await session.execute(stmt)
                return result.scalars().first()
        except Exception as e:
            logger.error(f"Failed to get model {model_id}: {e}")
            return None

    async def _get_embedder_for_model(self, model: Model) -> Embeddings:
        """Return LangChain embedder instance based on model provider config"""
        provider = model.provider
        if not provider:
            raise ValueError("Model provider not configured")

        cache_key = f"{provider.id}:{model.name}"
        if cache_key in self._embedder_cache:
            return self._embedder_cache[cache_key]

        embedder = await asyncio.to_thread(
            self._create_embedder,
            provider,
            model,
        )

        self._embedder_cache[cache_key] = embedder
        return embedder

    def _create_embedder(self, provider: ModelProvider, model: Model) -> Embeddings:
        """Construct concrete embedder instance"""
        interface_type = provider.interface_type

        if interface_type == PROVIDER_INTERFACE_TYPES["OPENAI"]:
            from langchain_openai import OpenAIEmbeddings

            kwargs = {"model": model.name}
            if provider.api_key:
                kwargs["openai_api_key"] = provider.api_key
            if provider.api_base_url:
                kwargs["openai_api_base"] = provider.api_base_url
            
            return OpenAIEmbeddings(**kwargs)
        elif interface_type == PROVIDER_INTERFACE_TYPES["DASHSCOPE"]:
            from langchain_community.embeddings import DashScopeEmbeddings
            kwargs = {"model": model.name}
            if provider.api_key:
                kwargs["dashscope_api_key"] = provider.api_key
            return DashScopeEmbeddings(**kwargs)
        raise NotImplementedError(
            f"Unsupported provider interface for embeddings: {interface_type}"
        )
