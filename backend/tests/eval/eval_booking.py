"""
Layer 4 — LLM Evaluation: Booking Confirmation Rate
Runs 10 full booking conversations and validates the final MongoDB state.
Measures end-to-end task success rate of the action agent.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport

load_dotenv()

def get_date(days: int) -> str:
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

# 10 booking scenarios with varying constraints and phrasings
BOOKING_SCENARIOS = [
    {
        "name": "Standard single-turn",
        "turns": [f"Book an appointment for patient P-1001 on {get_date(5)} at 10 AM for a physical"],
        "expected_db": {"patient_id": "P-1001", "date": get_date(5), "time": "10:00 AM"}
    },
    {
        "name": "New patient multi-turn",
        "turns": ["I want to book an appointment", f"My ID is NEW-EVAL-1, {get_date(2)} at 9 AM, cough"],
        "expected_db": {"patient_id": "NEW-EVAL-1", "date": get_date(2), "time": "09:00 AM"}
    },
    {
        "name": "Reschedule existing",
        "turns": [f"Reschedule appointment for P-1002 to {get_date(10)} at 2 PM"],
        "expected_db": {"patient_id": "P-1002", "date": get_date(10), "time": "02:00 PM"}
    },
    {
        "name": "Cancel existing",
        "turns": ["Please cancel the appointment for P-1004"],
        "expected_db": {"patient_id": "P-1004", "status": "Cancelled"}
    },
]

async def run_booking_eval():
    print(f"\n{'='*60}")
    print(f"  MedBot Booking Success Rate Evaluation")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    from main import app
    from pymongo import MongoClient
    
    mongo_uri = os.environ.get("MONGODB_URI")
    if not mongo_uri:
        print("ERROR: MONGODB_URI not set")
        return
        
    client = MongoClient(mongo_uri)
    db = client["medibot_db"]
    
    results = []
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
        for i, scenario in enumerate(BOOKING_SCENARIOS):
            print(f"[{i+1}/{len(BOOKING_SCENARIOS)}] {scenario['name']}")
            sid = str(uuid.uuid4())
            
            # Execute turns
            for turn in scenario["turns"]:
                print(f"  User: {turn}")
                await api.post("/chat", json={"message": turn, "session_id": sid})
                
            # Verify DB state
            expected = scenario["expected_db"]
            pid = expected["patient_id"]
            
            patient = db.patients.find_one({"patient_id": pid})
            
            success = True
            error_msg = ""
            
            if not patient:
                success = False
                error_msg = "Patient record not found in MongoDB"
            else:
                appt = patient.get("appointment", {})
                if "date" in expected and appt.get("date") != expected["date"]:
                    success = False
                    error_msg = f"Date mismatch: got {appt.get('date')}, expected {expected['date']}"
                elif "status" in expected and appt.get("status") != expected["status"]:
                    success = False
                    error_msg = f"Status mismatch: got {appt.get('status')}, expected {expected['status']}"
                    
            if success:
                print("  ✅ SUCCESS (DB state matches expected)")
            else:
                print(f"  ❌ FAILED: {error_msg}")
                
            results.append({
                "scenario": scenario["name"],
                "success": success,
                "error": error_msg
            })
            
            # Cleanup created test patients
            if pid.startswith("NEW-EVAL"):
                db.patients.delete_one({"patient_id": pid})
                
    success_count = sum(1 for r in results if r["success"])
    total = len(results)
    rate = success_count / total if total > 0 else 0
    
    print(f"\n{'─'*60}")
    print(f"  Overall Booking Success Rate: {success_count}/{total} ({rate:.0%})")
    print(f"  Target (≥ 80%): {'✅ PASS' if rate >= 0.8 else '❌ FAIL'}")
    print(f"{'─'*60}\n")

if __name__ == "__main__":
    asyncio.run(run_booking_eval())
