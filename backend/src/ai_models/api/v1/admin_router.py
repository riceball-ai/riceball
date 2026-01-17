import uuid
import httpx
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate as sqlalchemy_paginate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database import get_async_session
from src.ai_models.models import ModelProvider, Model
from .schemas import (
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelProviderResponse,
    ModelCreate,
    ModelUpdate,
    ModelResponse,
    ModelStatusEnum,
    ProviderStatusEnum,
    OllamaScanRequest
)

router = APIRouter()


# list all providers (non-paginated)
@router.get("/all-providers", response_model=list[ModelProviderResponse], summary="List all providers")
async def list_all_providers(
    session: AsyncSession = Depends(get_async_session)
):
    """List model providers with pagination and filtering"""
    query = select(ModelProvider)
    
    query = query.where(ModelProvider.status == ProviderStatusEnum.ACTIVE)
    
    result = await session.execute(query)

    return result.scalars().all()


# Provider list
@router.get("/providers", response_model=Page[ModelProviderResponse], summary="List model providers")
async def list_providers(
    status: Optional[ProviderStatusEnum] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in display_name"),
    session: AsyncSession = Depends(get_async_session)
):
    """List model providers with pagination and filtering"""
    query = select(ModelProvider)
    
    # Apply filters
    if status:
        query = query.where(ModelProvider.status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (ModelProvider.display_name.ilike(search_term))
        )
    
    return await sqlalchemy_paginate(session, query)


@router.post("/providers", response_model=ModelProviderResponse, summary="Create a new model provider")
async def create_provider(
    provider_data: ModelProviderCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new model provider"""
    
    provider = ModelProvider(**provider_data.model_dump())
    session.add(provider)
    await session.commit()
    await session.refresh(provider)
    return provider


# Provider detail endpoints - parameterized paths last
@router.get("/providers/{provider_id}", response_model=ModelProviderResponse, summary="Get a model provider")
async def get_provider(
    provider_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific model provider by ID"""
    result = await session.execute(
        select(ModelProvider).where(ModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    return provider


@router.put("/providers/{provider_id}", response_model=ModelProviderResponse, summary="Update a model provider")
async def update_provider(
    provider_id: uuid.UUID,
    provider_data: ModelProviderUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update a model provider"""
    result = await session.execute(
        select(ModelProvider).where(ModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    # Update fields
    update_data = provider_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    await session.commit()
    await session.refresh(provider)
    return provider


@router.delete("/providers/{provider_id}", summary="Delete a model provider")
async def delete_provider(
    provider_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a model provider and all associated models"""
    result = await session.execute(
        select(ModelProvider).where(ModelProvider.id == provider_id)
    )
    provider = result.scalar_one_or_none()
    
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    await session.delete(provider)
    await session.commit()
    return {"message": "Provider deleted successfully"}



@router.get("/all-models", response_model=list[ModelResponse], summary="List all models")
async def list_all_models(
    capabilities: Optional[List[str]] = Query(None, description="Filter model capabilities, return models containing all specified capabilities, multiple selection allowed"),
    session: AsyncSession = Depends(get_async_session)
):
    """List all models, support filtering by multiple capabilities (all must be included)"""
    query = select(Model).options(selectinload(Model.provider))
    query = query.where(Model.status == ModelStatusEnum.ACTIVE)
    result = await session.execute(query)
    models = result.scalars().all()
    
    # Filter capabilities at Python level to ensure database compatibility
    if capabilities:
        filtered_models = []
        for model in models:
            # Check if model contains all specified capabilities
            if all(cap in model.capabilities for cap in capabilities):
                filtered_models.append(model)
        return filtered_models
    
    return models


# Model list and create endpoints
@router.get("/models", response_model=Page[ModelResponse], summary="List models")
async def list_models(
    status: Optional[ModelStatusEnum] = Query(None, description="Filter by status"),
    provider_id: Optional[uuid.UUID] = Query(None, description="Filter by provider"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    search: Optional[str] = Query(None, description="Search in name or display_name"),
    session: AsyncSession = Depends(get_async_session)
):
    """List models with pagination and filtering"""
    query = select(Model).options(selectinload(Model.provider))
    
    # Apply filters
    if status:
        query = query.where(Model.status == status)
    
    if provider_id:
        query = query.where(Model.provider_id == provider_id)
    
    # Note: capability filtering is handled at Python level due to database compatibility issues
    # Not filtering at SQL level here
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Model.name.ilike(search_term)) |
            (Model.display_name.ilike(search_term))
        )
    
    # If capability filtering is present, filter at Python level before pagination
    if capability:
        # Get all results first
        result = await session.execute(query)
        all_models = result.scalars().all()
        
        # Filter at Python level
        filtered_models = [m for m in all_models if capability in m.capabilities]
        
        # Manually implement pagination (not optimal, but ensures compatibility)
        from fastapi_pagination import Params, Page as PageType
        
        # Get current pagination params
        params = Params()
        
        # Calculate pagination
        total = len(filtered_models)
        start = (params.page - 1) * params.size
        end = start + params.size
        page_items = filtered_models[start:end]
        
        return PageType.create(
            items=page_items,
            total=total,
            params=params
        )
    
    return await sqlalchemy_paginate(session, query)


@router.post("/models", response_model=ModelResponse, summary="Create a new model")
async def create_model(
    model_data: ModelCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new model"""
    # Check if provider exists
    provider_result = await session.execute(
        select(ModelProvider).where(ModelProvider.id == model_data.provider_id)
    )
    if not provider_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Provider not found")
    
    # Check if model with same name and provider already exists
    existing = await session.execute(
        select(Model).where(
            (Model.name == model_data.name) & 
            (Model.provider_id == model_data.provider_id)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Model with this name already exists for this provider")
    
    model = Model(**model_data.model_dump())
    session.add(model)
    await session.commit()
    await session.refresh(model, ["provider"])
    return model

# Model detail endpoints - parameterized paths last
@router.get("/models/{model_id}", response_model=ModelResponse, summary="Get a model")
async def get_model(
    model_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific model by ID"""
    result = await session.execute(
        select(Model)
        .options(selectinload(Model.provider))
        .where(Model.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return model


@router.put("/models/{model_id}", response_model=ModelResponse, summary="Update a model")
async def update_model(
    model_id: uuid.UUID,
    model_data: ModelUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """Update a model"""
    result = await session.execute(
        select(Model)
        .options(selectinload(Model.provider))
        .where(Model.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if provider exists if provider_id is being updated
    if model_data.provider_id and model_data.provider_id != model.provider_id:
        provider_result = await session.execute(
            select(ModelProvider).where(ModelProvider.id == model_data.provider_id)
        )
        if not provider_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Provider not found")
    
    # Check for name conflicts if name or provider is being updated
    if (model_data.name and model_data.name != model.name) or \
       (model_data.provider_id and model_data.provider_id != model.provider_id):
        check_name = model_data.name or model.name
        check_provider_id = model_data.provider_id or model.provider_id
        
        existing = await session.execute(
            select(Model).where(
                (Model.name == check_name) & 
                (Model.provider_id == check_provider_id) &
                (Model.id != model_id)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Model with this name already exists for this provider")
    
    # Update fields
    update_data = model_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(model, field, value)
    
    await session.commit()
    await session.refresh(model)
    return model


@router.delete("/models/{model_id}", summary="Delete a model")
async def delete_model(
    model_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    """Delete a model"""
    result = await session.execute(
        select(Model).where(Model.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    await session.delete(model)
    await session.commit()


@router.post("/providers/ollama/scan", response_model=List[ModelResponse], summary="Scan and import Ollama models")
async def scan_ollama_models(
    request: OllamaScanRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """Scan Ollama models from the given base URL and import them into the database."""
    base_url = request.base_url.rstrip("/")
    api_url = f"{base_url}/api/tags"
    
    # 1. Fetch models from Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(api_url)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to fetch models from Ollama: {response.text}")
            data = response.json()
            ollama_models = data.get("models", [])
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to Ollama at {base_url}: {str(e)}")
    
    if not ollama_models:
        return []

    # 2. Upsert Ollama Provider
    query = select(ModelProvider).where(ModelProvider.interface_type == "OLLAMA")
    result = await session.execute(query)
    provider = result.scalars().first()
    
    if not provider:
        # Create new provider
        provider = ModelProvider(
            display_name=request.provider_name,
            description="Auto-configured Ollama provider",
            api_base_url=f"{base_url}/v1",  # OpenAI compatible endpoint
            interface_type="OLLAMA",
            status=ProviderStatusEnum.ACTIVE,
            api_key="ollama"  # Dummy key
        )
        session.add(provider)
        await session.flush()  # Get ID
    else:
        # Update base_url if changed
        expected_api_base = f"{base_url}/v1"
        if provider.api_base_url != expected_api_base:
            provider.api_base_url = expected_api_base
            session.add(provider)
            await session.flush()
    
    # 3. Import Models
    # Get existing models for this provider
    existing_models_query = select(Model).where(Model.provider_id == provider.id)
    existing_models_result = await session.execute(existing_models_query)
    existing_models = {m.name: m for m in existing_models_result.scalars().all()}
    
    imported_models = []
    
    for om in ollama_models:
        model_name = om["name"]
        family = om.get("details", {}).get("family", "unknown")
        parameter_size = om.get("details", {}).get("parameter_size", "")
        
        display_name = f"{model_name} ({parameter_size})" if parameter_size else model_name
        
        # Decide capabilities (basic heuristic)
        capabilities = ["chat"]
        if family == "bert" or "embed" in model_name:
             capabilities = ["embedding"]
        
        if model_name in existing_models:
             model = existing_models[model_name]
             if model.status != ModelStatusEnum.ACTIVE:
                 model.status = ModelStatusEnum.ACTIVE
                 session.add(model)
             imported_models.append(model)
        else:
            # Create new model
            model = Model(
                name=model_name,
                display_name=display_name,
                description=f"Ollama model ({family})",
                provider_id=provider.id,
                status=ModelStatusEnum.ACTIVE,
                capabilities=capabilities,
                max_output_tokens=4096,  # Default guess
                max_context_tokens=8192  # Default guess
            )
            session.add(model)
            imported_models.append(model)
    
    await session.commit()
    
    # Refresh to get IDs
    for m in imported_models:
        await session.refresh(m)
        
    return imported_models
    return {"message": "Model deleted successfully"}
