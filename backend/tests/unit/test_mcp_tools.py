"""
Layer 1 — Unit Tests: MCP Tool Functions
Tests each MongoDB operation in isolation using mongomock.
No LLM calls, no network.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import mongomock
from unittest.mock import patch


# ── Helpers ──────────────────────────────────────────────────────────────────

def get_mcp_functions(col):
    """Import MCP tool functions with the collection patched to mongomock."""
    with patch("med_mcp.patients_collection", col):
        import med_mcp
        return med_mcp


# ── get_patient_details ───────────────────────────────────────────────────────

class TestGetPatientDetails:
    def test_returns_existing_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.get_patient_details("P-1001")
        assert "P-1001" in result
        assert "Alice Johnson" in result

    def test_returns_not_found_for_missing_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.get_patient_details("GHOST-999")
        assert "No patient found" in result

    def test_returns_appointment_info(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.get_patient_details("P-1001")
        assert "Annual Physical" in result or "Scheduled" in result


# ── cancel_appointment ────────────────────────────────────────────────────────

class TestCancelAppointment:
    def test_cancels_scheduled_appointment(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.cancel_appointment("P-1001")
        assert "Successfully cancelled" in result
        patient = seeded_collection.find_one({"patient_id": "P-1001"})
        assert patient["appointment"]["status"] == "Cancelled"

    def test_fails_for_nonexistent_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.cancel_appointment("GHOST-999")
        assert "Failed" in result

    def test_cancellation_is_persistent_in_db(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            med_mcp.cancel_appointment("P-1002")
        patient = seeded_collection.find_one({"patient_id": "P-1002"})
        assert patient["appointment"]["status"] == "Cancelled"


# ── book_appointment ──────────────────────────────────────────────────────────

class TestBookAppointment:
    def test_books_for_existing_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.book_appointment("P-1003", "2026-09-15", "10:00 AM", "Consultation")
        assert "Successfully booked" in result
        patient = seeded_collection.find_one({"patient_id": "P-1003"})
        assert patient["appointment"]["status"] == "Scheduled"
        assert patient["appointment"]["date"] == "2026-09-15"

    def test_creates_new_patient_via_upsert(self, seeded_collection):
        """book_appointment must create the record if patient doesn't exist."""
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.book_appointment("NEW-001", "2026-09-20", "09:00 AM", "cough", "John New")
        assert "Successfully booked" in result
        patient = seeded_collection.find_one({"patient_id": "NEW-001"})
        assert patient is not None
        assert patient["appointment"]["status"] == "Scheduled"
        assert patient["appointment"]["reason"] == "cough"

    def test_booking_writes_correct_fields(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            med_mcp.book_appointment("P-1003", "2026-10-01", "02:00 PM", "Annual Check")
        patient = seeded_collection.find_one({"patient_id": "P-1003"})
        assert patient["appointment"]["time"] == "02:00 PM"
        assert patient["appointment"]["reason"] == "Annual Check"

    def test_books_with_any_id_format(self, seeded_collection):
        """Patient IDs can be any string format."""
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.book_appointment("23456", "2026-09-05", "09:00 AM", "cough", "John Apparao")
        assert "Successfully booked" in result
        patient = seeded_collection.find_one({"patient_id": "23456"})
        assert patient is not None


# ── reschedule_appointment ────────────────────────────────────────────────────

class TestRescheduleAppointment:
    def test_reschedules_existing_appointment(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.reschedule_appointment("P-1001", "2026-10-10", "03:00 PM")
        assert "Successfully rescheduled" in result
        patient = seeded_collection.find_one({"patient_id": "P-1001"})
        assert patient["appointment"]["date"] == "2026-10-10"
        assert patient["appointment"]["time"] == "03:00 PM"
        assert patient["appointment"]["status"] == "Scheduled"

    def test_reschedule_fails_for_nonexistent_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.reschedule_appointment("GHOST-999", "2026-10-10", "03:00 PM")
        assert "Failed" in result


# ── register_patient ──────────────────────────────────────────────────────────

class TestRegisterPatient:
    def test_registers_new_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.register_patient("NEW-002", "Jane Doe", "555-9999", "jane@test.com")
        assert "Successfully registered" in result
        patient = seeded_collection.find_one({"patient_id": "NEW-002"})
        assert patient is not None
        assert patient["name"] == "Jane Doe"
        assert patient["appointment"]["status"] == "None"

    def test_does_not_duplicate_existing_patient(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            result = med_mcp.register_patient("P-1001", "Alice Johnson")
        assert "already exists" in result
        # Verify no duplicate
        count = seeded_collection.count_documents({"patient_id": "P-1001"})
        assert count == 1

    def test_new_patient_has_no_appointment(self, seeded_collection):
        with patch("med_mcp.patients_collection", seeded_collection):
            import med_mcp
            med_mcp.register_patient("NEW-003", "Mark Test")
        patient = seeded_collection.find_one({"patient_id": "NEW-003"})
        assert patient["appointment"]["status"] == "None"
        assert patient["appointment"]["date"] is None
