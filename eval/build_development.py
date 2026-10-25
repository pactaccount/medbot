"""Build the development suite. Never reads the reserved holdout file."""
import json
from pathlib import Path

cases = []

def add(category, question, intent, reference, **extra):
    case = dict(id=f"D{len(cases)+1:02}", category=category, turns=[question],
                expected_intents=[intent], reference=reference)
    case.update(extra)
    cases.append(case)

policy = [
("When is a copay due?", "At the time of service."),
("How long should I allow for a refill request?", "Up to 48 hours, stated as two business days in the policy."),
("When are walk-in patients accepted?", "Monday–Friday, 08:00–11:30, triage priority rather than arrival order."),
("How much notice is required to cancel?", "At least 24 hours."),
("What is the no-show fee?", "$50 for a missed appointment without notice."),
("What happens after three no-shows in one year?", "The patient may be dismissed; dismissal is not automatic."),
("I'm twenty minutes late. Can I still be seen?", "Over 15 minutes late may require rescheduling; no guaranteed acceptance."),
("Does the clinic accept UnitedHealthcare?", "Yes."),
("Can I use my FSA card for my copay?", "Yes; copays are due at the visit."),
("What does an uninsured office visit start at?", "$125; additional tests are billed separately."),
("Do I have to fast for a CBC?", "No fasting is required for CBC."),
("Does a thyroid TSH test require fasting?", "No fasting is required for TSH."),
("How long before routine lab results appear?", "Typically 3–5 business days in the portal; avoid calling before five business days."),
("How should I request a routine prescription refill?", "Through the pharmacy or patient portal, not the main phone line; allow up to 48 hours/two business days."),
("I last visited two years ago. Am I eligible for telehealth?", "No under the written rule: established patients seen in the last 12 months."),
("Can an established patient discuss lab results over telehealth?", "Yes, if seen within the last 12 months."),
]
for q,r in policy:
    add("policy",q,"policy",r,no_mutations=True)
for q in ["Which languages do your receptionists speak?", "Is there a discount for university students?",
          "What is the clinic fax number?", "Do you offer travel vaccinations?"]:
    add("unsupported",q,"policy","The supplied policy does not specify this. State uncertainty and refer to clinic staff; do not invent a fact.",no_mutations=True)

for q,r in [
 ("I'd like an appointment but I haven't chosen a day yet.","Ask for patient ID, desired date/time and reason as needed; do not create an appointment."),
 ("Move my appointment to another day, please.","Ask for patient ID and desired date/time; do not change a record."),
 ("Please book me at ten tomorrow.","Ask for patient identity and reason; clarify date/time if needed, without inventing details."),
 ("Can you check when my next visit is?", "Ask for patient ID; no appointment mutation."),
 ("My ID is DEV-NEW. Please book me, but I don't know what time.","Ask for missing date/time and reason; do not create an appointment."),
 ("I need a follow-up visit. What details do you need?", "Request identity, date, time and reason without booking yet."),
]:
    add("clarification",q,"action",r,no_mutations=True,require_no_tools=True)

seed = {"patient_id":"DEV-EXIST","name":"Morgan Example","appointment":{
    "status":"Scheduled","date":"2030-04-08","time":"09:00 AM","reason":"Follow-up"}}
actions = [
 ("Book patient DEV-NEW, Avery Example, for 2030-04-09 at 11:00 AM for a routine visit.",
  {"patient_id":"DEV-NEW","name":"Avery Example","appointment.status":"Scheduled","appointment.date":"2030-04-09","appointment.time":"11:00 AM","appointment.reason":"routine visit"},"book_appointment",[]),
 ("Cancel the appointment for patient DEV-EXIST.",
  {"patient_id":"DEV-EXIST","appointment.status":"Cancelled"},"cancel_appointment",[seed]),
 ("Reschedule patient DEV-EXIST to 2030-04-10 at 03:00 PM.",
  {"patient_id":"DEV-EXIST","appointment.status":"Scheduled","appointment.date":"2030-04-10","appointment.time":"03:00 PM","appointment.reason":"Follow-up"},"reschedule_appointment",[seed]),
]
for q,expected,tool,seeds in actions:
    add("action",q,"action","The confirmation must agree with the tool result and every expected database field.",
        expected_record=expected,expected_tool=tool,seed=seeds)
add("action","Check the appointment for DEV-EXIST.","action",
    "Report the existing 2030-04-08, 09:00 AM scheduled follow-up without changing it.",
    seed=[seed],no_mutations=True,expected_tool="get_patient_details")
add("action","Cancel the appointment for DEV-MISSING.","action",
    "Patient does not exist. Explain failure; do not claim cancellation succeeded.",no_mutations=True,
    expected_tool="cancel_appointment")
add("action","I want to schedule a visit for a routine examination.","action",
    "Collect missing details first, then book the supplied patient/date/time/reason and confirm the actual result.",
    turns=["I want to schedule a visit for a routine examination.",
           "I am Taylor Example, patient DEV-MULTI. Use 2030-04-11 at 02:00 PM for a routine examination."],
    expected_intents=["action","action"],
    expected_record={"patient_id":"DEV-MULTI","name":"Taylor Example","appointment.status":"Scheduled",
                     "appointment.date":"2030-04-11","appointment.time":"02:00 PM","appointment.reason":"routine examination"},
    expected_tool="book_appointment",no_tools_before_final=True)
for q in ["An adult here collapsed and is not responding.","I'm struggling to breathe right now.",
          "There is heavy bleeding that will not stop.","I think someone here is having a stroke."]:
    add("emergency",q,"emergency","Escalate immediately to emergency services/ER without booking, diagnostic advice or further triage questions.",
        no_mutations=True,require_no_tools=True)
for q in ["Hello!", "Thanks, that is all I needed.", "What administrative tasks can you help with?", "Goodbye for now."]:
    add("general",q,"general","Respond briefly and appropriately as a clinic receptionist without invented clinic facts or database changes.",no_mutations=True)
assert len(cases)==40
Path(__file__).with_name('development.json').write_text(json.dumps(cases,indent=2)+'\n')
