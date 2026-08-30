"""
Layer 2 — Integration Tests: Session Memory
Validates that chat_history persists correctly across turns in SESSION_STORE.
Uses real FastAPI app + mocked LLM (no real API calls).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _make_resp(content, intent="general"):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
class TestSessionMemory:

    async def test_first_turn_creates_session(self, api_client):
        triage = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy = _make_resp("We are open 8am to 6pm weekdays.")
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage, policy])):
            response = await api_client.post("/chat", json={"message": "What are your hours?"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    async def test_session_id_is_uuid(self, api_client):
        import uuid
        triage = _make_resp('{"intent": "general", "patient_id": null, "email": null}')
        policy = _make_resp("Hello there.")
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage, policy])):
            response = await api_client.post("/chat", json={"message": "Hi"})
        sid = response.json()["session_id"]
        uuid.UUID(sid)  # raises ValueError if not a valid UUID

    async def test_chat_history_grows_after_two_turns(self, api_client):
        import main
        triage1 = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy1 = _make_resp("We open at 8am.")
        triage2 = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy2 = _make_resp("We accept BlueCross.")

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage1, policy1])):
            r1 = await api_client.post("/chat", json={"message": "What are your hours?"})
        sid = r1.json()["session_id"]

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage2, policy2])):
            await api_client.post("/chat", json={"message": "Do you accept BlueCross?", "session_id": sid})

        history = main.SESSION_STORE[sid]
        assert len(history) == 4  # 2 turns × 2 messages each
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        assert history[2]["role"] == "user"
        assert history[3]["role"] == "assistant"

    async def test_chat_history_content_is_correct(self, api_client):
        import main
        triage = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy = _make_resp("We are open weekdays.")

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage, policy])):
            r = await api_client.post("/chat", json={"message": "Are you open on weekdays?"})
        sid = r.json()["session_id"]
        history = main.SESSION_STORE[sid]

        assert history[0]["content"] == "Are you open on weekdays?"
        assert "open" in history[1]["content"].lower()

    async def test_history_passed_to_agent_on_second_turn(self, api_client):
        """Verify that chat_history is injected into the graph on turn 2."""
        import main as main_module

        triage1 = _make_resp('{"intent": "action", "patient_id": null, "email": null}')
        # Simulate action agent asking for more info (no tool call)
        msg = MagicMock()
        msg.content = "Could you please provide your patient ID?"
        msg.tool_calls = None
        choice = MagicMock(); choice.message = msg
        action_resp = MagicMock(); action_resp.choices = [choice]

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage1, action_resp])):
            r1 = await api_client.post("/chat", json={"message": "I want to book an appointment"})
        sid = r1.json()["session_id"]

        captured_state = {}
        original_invoke = main_module.graph.ainvoke

        async def capture_invoke(state):
            captured_state.update(state)
            return await original_invoke(state)

        triage2 = _make_resp('{"intent": "action", "patient_id": "P-1001", "email": null}')
        msg2 = MagicMock(); msg2.content = "Got it, booking for P-1001."; msg2.tool_calls = None
        ch2 = MagicMock(); ch2.message = msg2
        action_resp2 = MagicMock(); action_resp2.choices = [ch2]

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage2, action_resp2])), \
             patch.object(main_module.graph, "ainvoke", side_effect=capture_invoke):
            await api_client.post("/chat", json={"message": "My ID is P-1001", "session_id": sid})

        # chat_history should now contain turn 1
        assert len(captured_state.get("chat_history", [])) == 2

    async def test_sessions_are_isolated(self, api_client):
        """Two different session IDs should never share history."""
        import main
        triage1 = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy1 = _make_resp("Session A response.")
        triage2 = _make_resp('{"intent": "policy", "patient_id": null, "email": null}')
        policy2 = _make_resp("Session B response.")

        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage1, policy1])):
            r1 = await api_client.post("/chat", json={"message": "Hello from A"})
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage2, policy2])):
            r2 = await api_client.post("/chat", json={"message": "Hello from B"})

        sid_a = r1.json()["session_id"]
        sid_b = r2.json()["session_id"]
        assert sid_a != sid_b
        assert main.SESSION_STORE[sid_a][0]["content"] == "Hello from A"
        assert main.SESSION_STORE[sid_b][0]["content"] == "Hello from B"
