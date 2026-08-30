"""
Layer 5 — Performance Tests: Latency Benchmarks
Measures the response time of different API flows to ensure SLA targets are met.
Does not require real DB (uses mock) but tests the full FastAPI layer.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import time
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
class TestLatency:
    
    async def test_emergency_latency(self):
        """Emergency should bypass MCP and respond quickly. Target: < 5s."""
        from main import app
        
        # Mock LLM to respond quickly with 'emergency'
        class MockChoice:
            class MockMsg:
                content = '{"intent": "emergency", "patient_id": null, "email": null}'
                tool_calls = None
            message = MockMsg()
            
        class MockResp:
            choices = [MockChoice()]
            
        with patch("med_agents.acompletion", new=AsyncMock(return_value=MockResp())):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                start_time = time.time()
                r = await client.post("/chat", json={"message": "I have severe chest pain"})
                elapsed = time.time() - start_time
                
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        # In mock environment this should be virtually instantaneous
        assert elapsed < 5.0, f"Emergency latency too high: {elapsed:.2f}s (Target < 5s)"
        
    async def test_policy_latency(self):
        """Policy requests require 2 LLM calls (triage + policy). Target: < 8s."""
        from main import app
        
        # Mock Triage
        class TriageChoice:
            class MockMsg:
                content = '{"intent": "policy", "patient_id": null, "email": null}'
                tool_calls = None
            message = MockMsg()
        class TriageResp: choices = [TriageChoice()]
        
        # Mock Policy
        class PolicyChoice:
            class MockMsg:
                content = "We are open Monday to Friday."
                tool_calls = None
            message = MockMsg()
        class PolicyResp: choices = [PolicyChoice()]
        
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[TriageResp(), PolicyResp()])):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                start_time = time.time()
                r = await client.post("/chat", json={"message": "What are your hours?"})
                elapsed = time.time() - start_time
                
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        assert elapsed < 8.0, f"Policy latency too high: {elapsed:.2f}s (Target < 8s)"
