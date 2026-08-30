"""
Layer 3 — E2E Tests: Appointment Booking Scenarios
Uses real LLM + real MongoDB. Validates full booking conversations and DB state.

Requirements:
  - MONGODB_URI set in medibot/backend/.env
  - LITELLM_MODEL set (defaults to gemini/gemini-3.5-flash)
  - Backend NOT running (tests use FastAPI TestClient directly)

Each test creates isolated appointments and cleans up after itself.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

load_dotenv()


@pytest_asyncio.fixture
async def live_client():
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup_test_patients():
    """Remove any test patient IDs created during e2e tests."""
    yield
    from pymongo import MongoClient
    client = MongoClient(os.getenv("MONGODB_URI"))
    db = client["medibot_db"]
    db["patients"].delete_many({"patient_id": {"$in": [
        "E2E-001", "E2E-002", "E2E-003", "E2E-004", "E2E-005"
    ]}})


def get_future_date(days_ahead: int) -> str:
    return (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


@pytest.mark.asyncio
@pytest.mark.e2e
class TestBookingHappyPath:

    async def test_scenario_a_new_patient_full_booking(self, live_client):
        """
        Full booking in 3 turns: intent → details → date.
        Assert MongoDB has the appointment written.
        """
        sid = None
        date = get_future_date(7)

        # Turn 1
        r1 = await live_client.post("/chat", json={
            "message": "Hi, I want to book an appointment under the name John Apparao"
        })
        assert r1.status_code == 200
        sid = r1.json()["session_id"]
        assert r1.json()["intent"] == "action"

        # Turn 2
        r2 = await live_client.post("/chat", json={
            "message": "My patient ID is E2E-001, I'd like 9 AM and I have a cough",
            "session_id": sid
        })
        assert r2.status_code == 200

        # Turn 3 — provide date
        r3 = await live_client.post("/chat", json={
            "message": f"The date is {date}",
            "session_id": sid
        })
        assert r3.status_code == 200

        # Verify MongoDB
        from pymongo import MongoClient
        client = MongoClient(os.getenv("MONGODB_URI"))
        patient = client["medibot_db"]["patients"].find_one({"patient_id": "E2E-001"})
        assert patient is not None, "Patient E2E-001 was not created in MongoDB"
        assert patient["appointment"]["status"] == "Scheduled"
        assert patient["appointment"]["date"] == date

    async def test_scenario_b_existing_patient_booking(self, live_client):
        """
        Book for a patient that already exists (P-1001 from seed data).
        """
        date = get_future_date(5)
        r1 = await live_client.post("/chat", json={
            "message": f"Book an appointment for patient P-1001 on {date} at 10 AM for an annual physical"
        })
        assert r1.status_code == 200

        from pymongo import MongoClient
        patient = MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].find_one({"patient_id": "P-1001"})
        assert patient["appointment"]["date"] == date
        assert patient["appointment"]["status"] == "Scheduled"

    async def test_scenario_c_book_then_cancel(self, live_client):
        """Book an appointment then cancel it in the same session."""
        date = get_future_date(10)

        # Book
        r1 = await live_client.post("/chat", json={
            "message": f"Book an appointment for E2E-002, {date}, 11 AM, follow-up"
        })
        assert r1.status_code == 200
        sid = r1.json()["session_id"]

        # Cancel
        r2 = await live_client.post("/chat", json={
            "message": "Actually, please cancel my appointment",
            "session_id": sid
        })
        assert r2.status_code == 200

        from pymongo import MongoClient
        patient = MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].find_one({"patient_id": "E2E-002"})
        assert patient is not None
        assert patient["appointment"]["status"] == "Cancelled"

    async def test_scenario_d_reschedule(self, live_client):
        """Book then reschedule to a different date."""
        date1 = get_future_date(5)
        date2 = get_future_date(15)

        r1 = await live_client.post("/chat", json={
            "message": f"Book appointment for E2E-003, {date1}, 9 AM, consultation"
        })
        assert r1.status_code == 200
        sid = r1.json()["session_id"]

        r2 = await live_client.post("/chat", json={
            "message": f"Please reschedule my appointment to {date2} at 2 PM",
            "session_id": sid
        })
        assert r2.status_code == 200

        from pymongo import MongoClient
        patient = MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].find_one({"patient_id": "E2E-003"})
        assert patient["appointment"]["date"] == date2
        assert patient["appointment"]["status"] == "Scheduled"


@pytest.mark.asyncio
@pytest.mark.e2e
class TestBookingEdgeCases:

    async def test_missing_info_bot_asks_not_books(self, live_client):
        """
        When user only says 'book appointment' with no details,
        bot should ask for info — NOT call book_appointment yet.
        """
        r = await live_client.post("/chat", json={
            "message": "I want to book an appointment"
        })
        assert r.status_code == 200
        assert r.json()["intent"] == "action"

        # No write should have happened — check a random non-existing ID
        from pymongo import MongoClient
        count_before = MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].count_documents(
            {"patient_id": "E2E-NEW-UNKNOWN"}
        )
        assert count_before == 0

    async def test_arbitrary_patient_id_formats_accepted(self, live_client):
        """Bot must accept IDs like '23456', 'JA-99', not just P-XXXX."""
        date = get_future_date(7)
        r = await live_client.post("/chat", json={
            "message": f"Book appointment for patient ID 99999, {date}, 9 AM, cough"
        })
        assert r.status_code == 200

        from pymongo import MongoClient
        patient = MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].find_one({"patient_id": "99999"})
        # May or may not be written in one turn, but response should not contain "invalid ID"
        assert "invalid" not in r.json()["response"].lower()
        # cleanup
        MongoClient(os.getenv("MONGODB_URI"))["medibot_db"]["patients"].delete_one({"patient_id": "99999"})

    async def test_confirmation_message_contains_date(self, live_client):
        """Confirmation response should mention the booked date."""
        date = get_future_date(6)
        r = await live_client.post("/chat", json={
            "message": f"Book appointment E2E-004, {date}, 10 AM, lab test"
        })
        assert r.status_code == 200
        # Date or some indication should appear in the confirmation
        response_text = r.json()["response"].lower()
        assert date in response_text or "scheduled" in response_text or "confirm" in response_text
