
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from app.schemas.ticket_schema import AppTicket

# Mock Redis and app initialization
mock_redis = AsyncMock()
with patch("app.core.redis.redis_client", mock_redis), \
     patch("app.main.app.router.lifespan_context"):
    from app.api.ticket import router
    from app.services.ticket_service import ticket_service

@pytest.mark.asyncio
async def test_create_ticket_schema_and_service_call():
    # 1. Prepare test data
    ticket_data = {
        "issueType": "法律咨询",
        "platform": "App",
        "briefFacts": "Test facts",
        "userRequest": "Test request",
        "peopleNeedingHelp": True,
        "conversationId": "conv-123"
    }
    
    # 2. Validate Schema
    ticket = AppTicket(**ticket_data)
    assert ticket.issue_type == "法律咨询"
    assert ticket.platform == "App"
    assert ticket.brief_facts == "Test facts"
    assert ticket.user_request == "Test request"
    assert ticket.people_needing_help is True
    assert ticket.conversation_id == "conv-123"
    
    # Check alias export
    exported = ticket.dict(by_alias=True, exclude_none=True)
    assert exported["issueType"] == "法律咨询"
    assert exported["peopleNeedingHelp"] is True

    # 3. Mock service
    mock_created_ticket = ticket.copy()
    mock_created_ticket.id = 1001
    mock_created_ticket.status = "pending"
    
    ticket_service.create_ticket = AsyncMock(return_value=mock_created_ticket)
    
    # 4. Call endpoint logic directly (simulating request)
    # We can import the function directly to test logic without full client setup if we want
    # but let's try to invoke the function handler.
    from app.api.ticket import create_ticket
    
    user_context = {"access_token": "mock_token", "user_id": 123}
    
    result = await create_ticket(ticket, user_context)
    
    # 5. Verify
    assert result.id == 1001
    assert result.issue_type == "法律咨询"
    
    # Verify service call
    ticket_service.create_ticket.assert_called_once()
    call_args = ticket_service.create_ticket.call_args
    assert call_args[0][0] == ticket
    assert call_args[0][1] == "mock_token"

@pytest.mark.asyncio
async def test_create_ticket_missing_token():
    from app.api.ticket import create_ticket
    
    ticket = AppTicket(issueType="test")
    user_context = {} # No token
    
    with pytest.raises(HTTPException) as excinfo:
        await create_ticket(ticket, user_context)
    
    assert excinfo.value.status_code == 401

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_create_ticket_schema_and_service_call())
    asyncio.run(test_create_ticket_missing_token())
    print("All tests passed!")
