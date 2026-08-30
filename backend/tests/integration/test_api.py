"""
Layer 2 — Integration Tests: FastAPI Endpoint Contract
Validates HTTP contract: status codes, response shape, headers.
LLM is mocked for determinism and speed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _policy_mocks():
    triage = MagicMock()
    triage.choices[0].message.content = '{"intent": "policy", "patient_id": null, "email": null}'
    triage.choices[0].message.tool_calls = None
    policy = MagicMock()
    policy.choices[0].message.content = "We are open weekdays 8am to 6pm."
    policy.choices[0].message.tool_calls = None
    return [triage, policy]


def _emergency_mocks():
    triage = MagicMock()
    triage.choices[0].message.content = '{"intent": "emergency", "patient_id": null, "email": null}'
    triage.choices[0].message.tool_calls = None
    return [triage]


@pytest.mark.asyncio
class TestChatEndpoint:

    async def test_returns_200_for_valid_request(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "general", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Hello, how can I help?"
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "Hello"})
        assert r.status_code == 200

    async def test_response_has_all_required_fields(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "general", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Hello!"
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "Hi"})
        body = r.json()
        assert "response" in body
        assert "session_id" in body
        assert "intent" in body
        assert "steps" in body

    async def test_response_field_is_string(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "policy", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Some answer."
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "Any question"})
        assert isinstance(r.json()["response"], str)
        assert len(r.json()["response"]) > 0

    async def test_steps_is_a_list(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "policy", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Answer."
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "hours?"})
        assert isinstance(r.json()["steps"], list)

    async def test_session_id_echoed_when_provided(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "general", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Ok."
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "Hi", "session_id": "my-test-session"})
        assert r.json()["session_id"] == "my-test-session"

    async def test_intent_field_is_valid_value(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "policy", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "Policy answer."
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": "What are your hours?"})
        assert r.json()["intent"] in ("policy", "action", "emergency", "general")

    async def test_emergency_returns_911_response(self, api_client):
        triage = MagicMock()
        triage.choices[0].message.content = '{"intent": "emergency", "patient_id": null, "email": null}'
        triage.choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(return_value=triage)):
            r = await api_client.post("/chat", json={"message": "I am having a heart attack"})
        assert r.status_code == 200
        assert r.json()["intent"] == "emergency"
        body = r.json()["response"].lower()
        assert "911" in body or "emergency" in body

    async def test_cors_options_returns_200(self, api_client):
        r = await api_client.options("/chat")
        assert r.status_code == 200

    async def test_missing_message_field_returns_422(self, api_client):
        r = await api_client.post("/chat", json={"session_id": "abc"})
        assert r.status_code == 422  # FastAPI validation error

    async def test_empty_message_handled_gracefully(self, api_client):
        mocks = [MagicMock(), MagicMock()]
        mocks[0].choices[0].message.content = '{"intent": "general", "patient_id": null, "email": null}'
        mocks[0].choices[0].message.tool_calls = None
        mocks[1].choices[0].message.content = "How can I help?"
        mocks[1].choices[0].message.tool_calls = None
        with patch("med_agents.acompletion", new=AsyncMock(side_effect=mocks)):
            r = await api_client.post("/chat", json={"message": ""})
        assert r.status_code == 200
        assert isinstance(r.json()["response"], str)
