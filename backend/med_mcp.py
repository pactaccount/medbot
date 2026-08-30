import os
from fastmcp import FastMCP
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("MedBot Server")
MONGO_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGO_URI)
db = client['medibot_db']
patients_collection = db['patients']

@mcp.tool()
def get_patient_details(patient_id: str) -> str:
    """Retrieve all appointment information for a specific patient by their ID."""
    patient = patients_collection.find_one({"patient_id": patient_id})
    if not patient:
        return f"No patient found with ID {patient_id}"
    return str(patient)

@mcp.tool()
def cancel_appointment(patient_id: str) -> str:
    """Cancel an appointment for a patient."""
    result = patients_collection.update_one(
        {"patient_id": patient_id},
        {"$set": {"appointment.status": "Cancelled"}}
    )
    if result.modified_count > 0:
        return f"Successfully cancelled appointment for {patient_id}."
    return f"Failed to cancel. Make sure the patient ID {patient_id} is correct and they have an appointment."

@mcp.tool()
def reschedule_appointment(patient_id: str, new_date: str, new_time: str) -> str:
    """Reschedule an existing appointment to a new date and time for a patient."""
    result = patients_collection.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "appointment.date": new_date,
            "appointment.time": new_time,
            "appointment.status": "Scheduled"
        }}
    )
    if result.modified_count > 0:
        return f"Successfully rescheduled appointment for {patient_id} to {new_date} at {new_time}."
    return f"Failed to reschedule. Make sure the patient ID {patient_id} is correct and has an existing appointment."

@mcp.tool()
def register_patient(patient_id: str, name: str, contact: str = "", email: str = "") -> str:
    """Register a new patient in the system if they don't already exist."""
    existing = patients_collection.find_one({"patient_id": patient_id})
    if existing:
        return f"Patient {patient_id} already exists as '{existing.get('name')}'. No need to re-register."
    patients_collection.insert_one({
        "patient_id": patient_id,
        "name": name,
        "contact": contact,
        "email": email,
        "appointment": {"status": "None", "date": None, "time": None, "reason": None}
    })
    return f"Successfully registered new patient {patient_id} ({name})."

@mcp.tool()
def book_appointment(patient_id: str, date: str, time: str, reason: str, patient_name: str = "") -> str:
    """Book a new appointment for a patient. Creates the patient record if they don't exist yet."""
    result = patients_collection.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "appointment.status": "Scheduled",
            "appointment.date": date,
            "appointment.time": time,
            "appointment.reason": reason
        },
         "$setOnInsert": {
            "patient_id": patient_id,
            "name": patient_name or patient_id,
            "contact": "",
            "email": ""
         }
        },
        upsert=True
    )
    if result.modified_count > 0 or result.upserted_id:
        return f"Successfully booked appointment for {patient_id} ({patient_name}) on {date} at {time} for {reason}."
    return f"Failed to book appointment for {patient_id}. Please try again."

if __name__ == "__main__":
    mcp.run(transport='stdio')
