import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGODB_URI")
if not MONGO_URI:
    raise ValueError("MONGODB_URI is not set in the .env file")

client = MongoClient(MONGO_URI)
db = client['medibot_db']
patients_collection = db['patients']

def setup_db():
    print("Connecting to MongoDB Atlas...")
    
    # Drop existing collection to start fresh
    patients_collection.drop()
    
    # Create 50 synthetic patients
    synthetic_patients = []
    statuses = ["Scheduled", "None", "Completed", "Cancelled"]
    reasons = ["Annual Physical", "Follow-up", "Consultation", "Lab Test", "Vaccination"]
    
    for i in range(1, 51):
        patient_id = f"P-{1000 + i}"
        status = statuses[i % len(statuses)]
        reason = reasons[i % len(reasons)] if status == "Scheduled" else None
        
        patient = {
            "patient_id": patient_id,
            "name": f"Patient Name {i}",
            "contact": f"555-01{i:02d}",
            "email": f"patient{i}@example.com",
            "appointment": {
                "status": status,
                "date": f"2026-09-0{i%9+1}" if status == "Scheduled" else None,
                "time": f"0{i%4+8}:00 AM" if status == "Scheduled" else None,
                "reason": reason
            }
        }
        synthetic_patients.append(patient)
        
    result = patients_collection.insert_many(synthetic_patients)
    print(f"Successfully seeded {len(result.inserted_ids)} patients into the database.")

if __name__ == "__main__":
    setup_db()
