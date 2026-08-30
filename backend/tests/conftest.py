"""
conftest.py — Shared fixtures for all MedBot test layers.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
import mongomock
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

# ── Seed data ────────────────────────────────────────────────────────────────

TEST_PATIENTS = [
    {
        "patient_id": "P-1001",
        "name": "Alice Johnson",
        "contact": "555-0101",
        "email": "alice@example.com",
        "appointment": {"status": "Scheduled", "date": "2026-09-01", "time": "09:00 AM", "reason": "Annual Physical"},
    },
    {
        "patient_id": "P-1002",
        "name": "Bob Smith",
        "contact": "555-0102",
        "email": "bob@example.com",
        "appointment": {"status": "Scheduled", "date": "2026-09-02", "time": "10:00 AM", "reason": "Follow-up"},
    },
    {
        "patient_id": "P-1003",
        "name": "Carol Davis",
        "contact": "555-0103",
        "email": "carol@example.com",
        "appointment": {"status": "Cancelled", "date": None, "time": None, "reason": None},
    },
    {
        "patient_id": "P-1004",
        "name": "Dan Williams",
        "contact": "555-0104",
        "email": "dan@example.com",
        "appointment": {"status": "Scheduled", "date": "2026-09-05", "time": "11:00 AM", "reason": "Consultation"},
    },
    {
        "patient_id": "P-1005",
        "name": "Eve Martinez",
        "contact": "555-0105",
        "email": "eve@example.com",
        "appointment": {"status": "Scheduled", "date": "2026-09-08", "time": "02:00 PM", "reason": "Lab Test"},
    },
]


@pytest.fixture(scope="session")
def test_patients():
    return TEST_PATIENTS


# ── MongoDB mock ──────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_collection():
    """Fresh mongomock collection seeded with TEST_PATIENTS."""
    with mongomock.patch(servers=(("mongodb.test", 27017),)):
        from pymongo import MongoClient
        client = MongoClient("mongodb://mongodb.test:27017/")
        db = client["medibot_test_db"]
        col = db["patients"]
        col.insert_many([p.copy() for p in TEST_PATIENTS])
        yield col
        col.drop()


# ── LLM mock helpers ──────────────────────────────────────────────────────────

def _make_llm_response(content: str, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def mock_llm_action():
    triage_resp = _make_llm_response('{"intent": "action", "patient_id": null, "email": null}')
    tool_call = MagicMock()
    tool_call.id = "tc-001"
    tool_call.function.name = "book_appointment"
    tool_call.function.arguments = '{"patient_id": "TEST-001", "date": "2026-09-10", "time": "09:00 AM", "reason": "cough", "patient_name": "Test User"}'
    action_resp = _make_llm_response("", tool_calls=[tool_call])
    action_resp.choices[0].message.model_dump = lambda: {
        "role": "assistant", "content": None, "tool_calls": [tool_call]
    }
    final_resp = _make_llm_response("Your appointment is confirmed for 2026-09-10 at 09:00 AM.")
    with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage_resp, action_resp, final_resp])):
        yield


@pytest.fixture
def mock_llm_policy():
    triage_resp = _make_llm_response('{"intent": "policy", "patient_id": null, "email": null}')
    policy_resp = _make_llm_response("Our clinic is open Monday through Friday, 8am to 6pm.")
    with patch("med_agents.acompletion", new=AsyncMock(side_effect=[triage_resp, policy_resp])):
        yield


@pytest.fixture
def mock_llm_emergency():
    triage_resp = _make_llm_response('{"intent": "emergency", "patient_id": null, "email": null}')
    with patch("med_agents.acompletion", new=AsyncMock(return_value=triage_resp)):
        yield


# ── FastAPI client ────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def api_client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ── Session store reset ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_session_store():
    import main
    main.SESSION_STORE.clear()
    yield
    main.SESSION_STORE.clear()
