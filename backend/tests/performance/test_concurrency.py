"""
Layer 5 — Performance Tests: Concurrency
Validates that MedBot can handle multiple simultaneous sessions
without memory bleeding or crashing.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestConcurrency:
    
    async def test_concurrent_sessions_isolated(self):
        """Simulate 10 concurrent users sending messages at exactly the same time."""
        from main import app, SESSION_STORE
        
        # Mock LLM to return immediately to focus on API/Concurrency logic
        class MockChoice:
            class MockMsg:
                content = '{"intent": "policy", "patient_id": null, "email": null}'
                tool_calls = None
            message = MockMsg()
        class MockResp: choices = [MockChoice()]
        
        # Policy response mock
        class PolicyChoice:
            class MockMsg:
                content = "Concurrency test response."
                tool_calls = None
            message = MockMsg()
        class PolicyResp: choices = [PolicyChoice()]
        
        async def simulate_user(client, user_id):
            msg = f"Message from user {user_id}"
            r = await client.post("/chat", json={"message": msg})
            return user_id, msg, r.json()
            
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[MockResp(), PolicyResp()] * 10)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Launch 10 requests concurrently
                tasks = [simulate_user(client, i) for i in range(10)]
                results = await asyncio.gather(*tasks)
                
        # Validate results
        assert len(results) == 10
        session_ids = set()
        
        for user_id, original_msg, resp_data in results:
            sid = resp_data["session_id"]
            session_ids.add(sid)
            
            # Verify session history isolation
            history = SESSION_STORE[sid]
            assert len(history) == 2, "Session history should have exactly 1 turn (2 messages)"
            assert history[0]["content"] == original_msg, "Session history mixed up between concurrent users!"
            
        # Ensure 10 unique sessions were created
        assert len(session_ids) == 10, "Race condition in session ID generation/assignment!"
