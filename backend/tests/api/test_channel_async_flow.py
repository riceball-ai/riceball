import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import BackgroundTasks
from src.channels.api.v1.webhook_router import channel_webhook
from uuid import uuid4

@pytest.mark.asyncio
async def test_webhook_async_flow():
    # Mock dependencies
    channel_id = uuid4()
    mock_request = MagicMock()
    mock_bg_tasks = MagicMock(spec=BackgroundTasks)
    mock_session = AsyncMock()
    
    # Mock ChannelService
    with patch("src.channels.api.v1.webhook_router.ChannelService") as MockServiceClass:
        mock_service = AsyncMock()
        MockServiceClass.return_value = mock_service
        
        # Scenario: Service returns async payload
        mock_service.handle_webhook.return_value = {
            "async_task_payload": {
                "user_id": "test_user",
                "content": "hello"
            }
        }
        
        # Execute Router
        response = await channel_webhook(
            channel_id=channel_id, 
            request=mock_request, 
            background_tasks=mock_bg_tasks,
            session=mock_session
        )
        
        # Verify 
        # 1. Immediate response
        assert response == {"status": "processing"}
        
        # 2. Background task added
        mock_bg_tasks.add_task.assert_called_once()
        args, kwargs = mock_bg_tasks.add_task.call_args
        # Inspect the task function and arguments
        # args[0] is the function 'process_incoming_message'
        # Check kwargs
        assert kwargs['user_id'] == "test_user"
        assert kwargs['channel_id'] == channel_id
        assert kwargs['text'] == "hello"
