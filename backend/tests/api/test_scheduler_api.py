import pytest
import uuid
from unittest.mock import patch
from src.users.models import User
from src.ai_models.models import Model, ModelProvider, ModelStatusEnum, ProviderStatusEnum
from src.assistants.models import Assistant, AssistantStatusEnum
from src.channels.models import UserChannelBinding, ChannelConfig
from src.auth import current_active_user
from src.main import app

@pytest.mark.asyncio
async def test_scheduler_crud_flow(client, session, setup_database):
    # 1. Setup Data
    user_id = uuid.uuid4()
    user = User(
        id=user_id, 
        email="scheduler_test@example.com", 
        hashed_password="fake", 
        is_active=True, 
        is_verified=True,
        is_superuser=False
    )
    session.add(user)
    
    provider = ModelProvider(
        id=uuid.uuid4(),
        display_name="OpenAI",
        api_base_url="https://api.openai.com/v1",
        interface_type="OPENAI",
        status=ProviderStatusEnum.ACTIVE
    )
    session.add(provider)
    
    model = Model(
        id=uuid.uuid4(),
        name="gpt-4o",
        display_name="GPT-4o",
        provider_id=provider.id,
        status=ModelStatusEnum.ACTIVE,
        capabilities=["chat"],
        generation_config={}
    )
    session.add(model)
    
    assistant = Assistant(
        id=uuid.uuid4(),
        name="Test Assistant",
        model_id=model.id,
        owner_id=user.id,
        status=AssistantStatusEnum.ACTIVE,
        config={},
        temperature=1.0
    )
    session.add(assistant)
    
    # Needs a channel config for binding? Optional in binding model (nullable=True).
    binding = UserChannelBinding(
        id=uuid.uuid4(),
        user_id=user.id,
        provider="telegram",
        external_user_id="12345",
        metadata_={}
    )
    session.add(binding)
    
    await session.commit()
    
    # 2. Override Auth
    app.dependency_overrides[current_active_user] = lambda: user

    # 3. Test Create
    payload = {
        "name": "Daily Report",
        "cron_expression": "0 8 * * *",
        "assistant_id": str(assistant.id),
        "prompt_template": "Report status.",
        "target_binding_id": str(binding.id),
        "is_active": True
    }
    
    # Patch the scheduler core functions to avoid real scheduling
    with patch("src.scheduler.api.v1.user_router.add_job_to_scheduler") as mock_add, \
         patch("src.scheduler.api.v1.user_router.remove_job_from_scheduler") as mock_remove:
         
        # CREATE
        response = await client.post("/api/v1/scheduled-tasks/", json=payload)
        assert response.status_code == 201, response.text
        data = response.json()
        task_id = data["id"]
        assert data["name"] == "Daily Report"
        mock_add.assert_called_once()
        
        # LIST
        response = await client.get("/api/v1/scheduled-tasks/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == task_id
        
        # UPDATE
        patch_payload = {"cron_expression": "0 9 * * *"}
        response = await client.patch(f"/api/v1/scheduled-tasks/{task_id}", json=patch_payload)
        assert response.status_code == 200
        assert response.json()["cron_expression"] == "0 9 * * *"
        # Called twice: once for create, once for update
        assert mock_add.call_count == 2 
        
        # DELETE
        response = await client.delete(f"/api/v1/scheduled-tasks/{task_id}")
        assert response.status_code == 204
        mock_remove.assert_called_with(str(task_id))
        
        # Verify empty list
        response = await client.get("/api/v1/scheduled-tasks/")
        assert len(response.json()) == 0
