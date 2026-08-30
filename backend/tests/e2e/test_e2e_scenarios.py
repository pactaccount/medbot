"""
Layer 3 — E2E Tests: Policy & Emergency Scenarios
Uses real LLM. Validates intent classification and response content.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()


@pytest_asyncio.fixture
async def live_client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Policy Tests ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.e2e
class TestPolicyScenarios:

    async def test_fasting_policy(self, live_client):
        r = await live_client.post("/chat", json={"message": "Do I need to fast before blood work?"})
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        response = r.json()["response"].lower()
        assert "fast" in response or "8 hour" in response or "hour" in response

    async def test_clinic_hours(self, live_client):
        r = await live_client.post("/chat", json={"message": "What time does the clinic open?"})
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        response = r.json()["response"].lower()
        assert "am" in response or "8" in response or "monday" in response

    async def test_insurance_acceptance(self, live_client):
        r = await live_client.post("/chat", json={"message": "Do you accept Aetna insurance?"})
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        response = r.json()["response"].lower()
        assert "aetna" in response

    async def test_cancellation_policy(self, live_client):
        r = await live_client.post("/chat", json={"message": "What is your cancellation policy?"})
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        response = r.json()["response"].lower()
        assert "cancel" in response or "24" in response or "fee" in response

    async def test_saturday_hours(self, live_client):
        r = await live_client.post("/chat", json={"message": "Are you open on Saturdays?"})
        assert r.status_code == 200
        assert r.json()["intent"] == "policy"
        response = r.json()["response"].lower()
        assert "saturday" in response

    async def test_policy_steps_populated(self, live_client):
        r = await live_client.post("/chat", json={"message": "Do I need to fast?"})
        assert r.status_code == 200
        steps = r.json()["steps"]
        assert isinstance(steps, list)
        assert len(steps) >= 2  # At minimum: triage step + policy step

    async def test_unknown_policy_returns_empathetic_response(self, live_client):
        """Bot should not crash or give a blank response for unknown questions."""
        r = await live_client.post("/chat", json={"message": "Do you offer home visit services?"})
        assert r.status_code == 200
        response = r.json()["response"]
        assert len(response) > 20  # Non-empty, substantive response
        assert "error" not in response.lower()


# ── Emergency Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.e2e
class TestEmergencyScenarios:

    async def test_chest_pain_triggers_emergency(self, live_client):
        r = await live_client.post("/chat", json={"message": "I have severe chest pain"})
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        response = r.json()["response"].lower()
        assert "911" in response or "emergency room" in response or "immediately" in response

    async def test_breathing_difficulty_triggers_emergency(self, live_client):
        r = await live_client.post("/chat", json={"message": "I can't breathe"})
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        response = r.json()["response"].lower()
        assert "911" in response or "emergency" in response

    async def test_severe_bleeding_triggers_emergency(self, live_client):
        r = await live_client.post("/chat", json={"message": "I'm bleeding heavily and can't stop it"})
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"

    async def test_heart_attack_triggers_emergency(self, live_client):
        r = await live_client.post("/chat", json={"message": "I think I'm having a heart attack"})
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        response = r.json()["response"].lower()
        # SAFETY CRITICAL: must mention 911 or ER
        assert "911" in response or "emergency room" in response

    async def test_emergency_response_is_fast(self, live_client):
        """Emergency responses require no MCP tool call — should be faster than action."""
        import time
        start = time.time()
        r = await live_client.post("/chat", json={"message": "I have severe chest pain and can't breathe"})
        elapsed = time.time() - start
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        assert elapsed < 15, f"Emergency response took {elapsed:.1f}s — too slow"

    async def test_emergency_does_not_call_mcp_tools(self, live_client):
        """Emergency path should bypass all tool calls."""
        r = await live_client.post("/chat", json={"message": "I'm having a stroke"})
        assert r.status_code == 200
        steps = r.json()["steps"]
        # Should NOT have any "Tool called" step
        tool_steps = [s for s in steps if "Tool called" in s]
        assert len(tool_steps) == 0


# ── Triage Context Tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.e2e
class TestTriageContextAwareness:

    async def test_followup_detail_classified_as_action(self, live_client):
        """After starting a booking, follow-up with just an ID should still be 'action'."""
        r1 = await live_client.post("/chat", json={"message": "I want to book an appointment"})
        assert r1.json()["intent"] == "action"
        sid = r1.json()["session_id"]

        r2 = await live_client.post("/chat", json={
            "message": "My patient ID is E2E-TRIAGE-001",
            "session_id": sid
        })
        assert r2.json()["intent"] == "action", (
            f"Follow-up was misclassified as '{r2.json()['intent']}' — context lost"
        )

    async def test_vague_date_followup_classified_as_action(self, live_client):
        """'day after tomorrow' after a booking intent should stay as action."""
        r1 = await live_client.post("/chat", json={
            "message": "Book appointment for E2E-TRIAGE-002, 9 AM, cough"
        })
        sid = r1.json()["session_id"]

        r2 = await live_client.post("/chat", json={
            "message": "day after tomorrow",
            "session_id": sid
        })
        assert r2.json()["intent"] == "action", (
            f"Vague date reply classified as '{r2.json()['intent']}' — context lost"
        )

    async def test_new_session_does_not_inherit_history(self, live_client):
        """A fresh session should not carry over intent from a previous session."""
        # Session A: booking
        r1 = await live_client.post("/chat", json={"message": "Book an appointment"})
        assert r1.json()["intent"] == "action"

        # Session B: completely new session with a policy question
        r2 = await live_client.post("/chat", json={"message": "What are your opening hours?"})
        assert r2.json()["intent"] == "policy"
        assert r2.json()["session_id"] != r1.json()["session_id"]
