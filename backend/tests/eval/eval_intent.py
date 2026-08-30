"""
Layer 4 — LLM Evaluation: Intent Classification Accuracy
Runs a 40-message golden dataset through the triage agent and measures accuracy.
Produces a detailed report with per-class metrics and confusion matrix.

Run: venv/bin/python tests/eval/eval_intent.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import asyncio
import json
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# ── Golden Dataset ────────────────────────────────────────────────────────────

GOLDEN_DATASET = [
    # ── action (14 examples) ──
    {"message": "I want to book an appointment",                                "expected": "action"},
    {"message": "Can you schedule me for next Tuesday at 10 AM?",               "expected": "action"},
    {"message": "My ID is P-1001, please cancel my appointment",                "expected": "action"},
    {"message": "I need to reschedule my appointment to next week",              "expected": "action"},
    {"message": "Book me in for a check-up, patient ID 23456",                  "expected": "action"},
    {"message": "id is 23456, time morning 9 and i have cough",                 "expected": "action"},
    {"message": "day after tomorrow",                                            "expected": "action"},  # follow-up (needs history)
    {"message": "2026-09-10 please",                                             "expected": "action"},  # follow-up date
    {"message": "Can I get an appointment for Monday morning?",                  "expected": "action"},
    {"message": "Please cancel appointment for patient John, ID JA-99",          "expected": "action"},
    {"message": "Move my appointment from Tuesday to Thursday",                  "expected": "action"},
    {"message": "I want to see a doctor as soon as possible",                    "expected": "action"},
    {"message": "schedule me for a blood test next week",                        "expected": "action"},
    {"message": "9 AM works for me, my patient number is 88888",                 "expected": "action"},

    # ── policy (10 examples) ──
    {"message": "What are your opening hours?",                                  "expected": "policy"},
    {"message": "Do I need to fast before a blood test?",                        "expected": "policy"},
    {"message": "Do you accept Aetna insurance?",                                "expected": "policy"},
    {"message": "What is your cancellation policy?",                             "expected": "policy"},
    {"message": "Are you open on Saturdays?",                                    "expected": "policy"},
    {"message": "How long do appointments typically take?",                      "expected": "policy"},
    {"message": "Do you accept walk-in patients?",                               "expected": "policy"},
    {"message": "What documents do I need to bring for my first visit?",         "expected": "policy"},
    {"message": "Do you offer telehealth or video consultations?",               "expected": "policy"},
    {"message": "Is parking available near the clinic?",                         "expected": "policy"},

    # ── emergency (8 examples) ──
    {"message": "I'm having a heart attack",                                     "expected": "emergency"},
    {"message": "I can't breathe and I feel dizzy",                              "expected": "emergency"},
    {"message": "My child is unconscious",                                       "expected": "emergency"},
    {"message": "I have severe chest pain",                                      "expected": "emergency"},
    {"message": "I'm bleeding heavily from a cut and it won't stop",             "expected": "emergency"},
    {"message": "I think I'm having a stroke, my face feels numb",               "expected": "emergency"},
    {"message": "Someone here is not breathing",                                 "expected": "emergency"},
    {"message": "I took too many pills by accident",                             "expected": "emergency"},

    # ── general (8 examples) ──
    {"message": "Hi there!",                                                     "expected": "general"},
    {"message": "Thank you so much for your help",                               "expected": "general"},
    {"message": "That's great, thanks",                                          "expected": "general"},
    {"message": "Can you repeat that?",                                          "expected": "general"},
    {"message": "I have a question",                                             "expected": "general"},
    {"message": "Goodbye",                                                       "expected": "general"},
    {"message": "You're very helpful",                                           "expected": "general"},
    {"message": "What can you help me with?",                                    "expected": "general"},
]


# ── Evaluator ─────────────────────────────────────────────────────────────────

async def evaluate_single(item: dict) -> dict:
    """Run one message through the triage agent and return actual vs expected intent."""
    from med_agents import build_graph

    graph = build_graph()
    state = {
        "ticket_id": "eval",
        "email_content": item["message"],
        "messages": [],
        "chat_history": [],
        "intent": "",
        "extracted_info": {},
        "final_response": "",
        "steps": [],
    }
    try:
        # Only run triage, not the full graph
        from med_agents import triage_agent
        result = await triage_agent(state)
        actual = result.get("intent", "general")
    except Exception as e:
        actual = f"ERROR: {e}"

    return {
        "message": item["message"],
        "expected": item["expected"],
        "actual": actual,
        "correct": actual == item["expected"],
    }


async def run_evaluation():
    print(f"\n{'='*60}")
    print(f"  MedBot Intent Classification Evaluation")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = []
    for i, item in enumerate(GOLDEN_DATASET):
        print(f"[{i+1:02d}/{len(GOLDEN_DATASET)}] Testing: '{item['message'][:55]}...' ", end="", flush=True)
        result = await evaluate_single(item)
        results.append(result)
        status = "✅" if result["correct"] else f"❌ (got '{result['actual']}')"
        print(status)

    # ── Compute metrics ───────────────────────────────────────────────────────
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = correct / total

    # Per-class accuracy
    classes = ["action", "policy", "emergency", "general"]
    class_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    confusion = defaultdict(lambda: defaultdict(int))

    for r in results:
        expected = r["expected"]
        actual = r["actual"] if r["actual"] in classes else "unknown"
        class_stats[expected]["total"] += 1
        if r["correct"]:
            class_stats[expected]["correct"] += 1
        confusion[expected][actual] += 1

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  RESULTS SUMMARY")
    print(f"{'─'*60}")
    print(f"  Overall Accuracy:  {correct}/{total}  ({accuracy:.1%})")

    target_met = accuracy >= 0.90
    print(f"  Target (≥ 90%):   {'✅ PASS' if target_met else '❌ FAIL'}")

    print(f"\n  Per-Class Accuracy:")
    for cls in classes:
        stats = class_stats[cls]
        if stats["total"] == 0:
            continue
        cls_acc = stats["correct"] / stats["total"]
        bar = "█" * int(cls_acc * 20) + "░" * (20 - int(cls_acc * 20))
        print(f"    {cls:10s}: {stats['correct']}/{stats['total']}  [{bar}]  {cls_acc:.0%}")

    # Safety check
    emergency_stats = class_stats["emergency"]
    false_negative_rate = 1 - (emergency_stats["correct"] / max(emergency_stats["total"], 1))
    print(f"\n  ⚠️  Emergency False-Negative Rate: {false_negative_rate:.0%}  (Target: 0%)")
    print(f"  {'✅ SAFE' if false_negative_rate == 0 else '🚨 SAFETY VIOLATION — Review immediately!'}")

    print(f"\n  Confusion Matrix:")
    header = f"{'':>12}" + "".join(f"{c:>10}" for c in classes)
    print(f"    {header}")
    for expected in classes:
        row = f"{'['+expected+']':>12}" + "".join(f"{confusion[expected][actual]:>10}" for actual in classes)
        print(f"    {row}")

    # Failures
    failures = [r for r in results if not r["correct"]]
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for f in failures:
            print(f"    Expected '{f['expected']}' → Got '{f['actual']}'")
            print(f"    Message: \"{f['message'][:70]}\"")

    # Save JSON report
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_accuracy": accuracy,
        "target_met": target_met,
        "emergency_false_negative_rate": false_negative_rate,
        "per_class": {cls: class_stats[cls] for cls in classes},
        "results": results,
    }
    report_path = os.path.join(os.path.dirname(__file__), "eval_intent_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📄 Full report saved to: {report_path}")
    print(f"{'='*60}\n")

    return accuracy


if __name__ == "__main__":
    accuracy = asyncio.run(run_evaluation())
    sys.exit(0 if accuracy >= 0.90 else 1)
