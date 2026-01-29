import sys
from unittest.mock import MagicMock

# Mock redis module
mock_redis = MagicMock()
mock_redis.asyncio = MagicMock()
sys.modules["redis"] = mock_redis
sys.modules["redis.asyncio"] = mock_redis.asyncio

import os
from unittest.mock import AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock app.initialize.redis
# Since app.services.ticket_service imports app.initialize.redis
# we need to ensure that import works.
# app.initialize.redis imports redis.asyncio as redis, which we mocked.

from app.api.ticket import router as ticket_router
from app.services.ticket_service import ticket_service
from app.core.security import get_current_session

# Create a minimal app for testing
app = FastAPI()
app.include_router(ticket_router)

client = TestClient(app)

# Mock user session
async def mock_get_current_session():
    return {"user_id": "test_user_123", "username": "test_user"}

app.dependency_overrides[get_current_session] = mock_get_current_session

def test_create_ticket():
    # Mock ticket_service.create_ticket
    ticket_service.create_ticket = AsyncMock(return_value={
        "id": "ticket_123",
        "title": "Test Ticket",
        "description": "Test Description",
        "conversation_id": "conv_123",
        "priority": "high",
        "type": "general",
        "status": "open",
        "user_id": "test_user_123",
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00"
    })
    
    response = client.post(
        "/app/ticket/createTicket",
        json={
            "title": "Test Ticket",
            "description": "Test Description",
            "conversation_id": "conv_123",
            "priority": "high",
            "type": "general"
        }
    )
    
    if response.status_code != 200:
        print(f"Create Ticket failed: {response.text}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "ticket_123"
    assert data["title"] == "Test Ticket"
    print("test_create_ticket passed")

def test_get_ticket_list():
    ticket_service.get_ticket_list = AsyncMock(return_value={
        "total": 1,
        "items": [{
            "id": "ticket_123",
            "title": "Test Ticket",
            "description": "Test Description",
            "conversation_id": "conv_123",
            "priority": "high",
            "type": "general",
            "status": "open",
            "user_id": "test_user_123",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }],
        "page": 1,
        "page_size": 10
    })
    
    response = client.get("/app/ticket/getTicketList?page=1&pageSize=10")
    
    if response.status_code != 200:
        print(f"Get List failed: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "ticket_123"
    print("test_get_ticket_list passed")

def test_update_ticket_status():
    # Mock get_ticket_detail to return a object with user_id
    mock_ticket = MagicMock()
    mock_ticket.user_id = "test_user_123"
    mock_ticket.status = "open"
    ticket_service.get_ticket_detail = AsyncMock(return_value=mock_ticket)
    
    ticket_service.update_ticket_status = AsyncMock(return_value=True)
    
    response = client.post(
        "/app/ticket/updateTicketStatus",
        json={"id": "ticket_123", "status": "closed"}
    )
    
    if response.status_code != 200:
        print(f"Update Status failed: {response.text}")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "closed"
    print("test_update_ticket_status passed")

if __name__ == "__main__":
    try:
        test_create_ticket()
        test_get_ticket_list()
        test_update_ticket_status()
        print("All tests passed!")
    except Exception as e:
        print(f"Tests failed: {e}")
        import traceback
        traceback.print_exc()
