# MedBot Clinic Portal

MedBot is an intelligent, multi-agent autonomous medical receptionist designed to automate clinic administrative workflows, answer policy questions, and escalate medical emergencies. Built with LangGraph, Model Context Protocol (MCP), and a modern React frontend.

## Key Features

*   **Multi-Agent Orchestration (LangGraph):** Routes queries intelligently between specialized agents:
    *   **Triage Agent:** Classifies user intent (Action, Policy, Emergency, General) using conversation history.
    *   **Action Agent:** Uses MCP tools to interact with the database (book, cancel, reschedule).
    *   **Policy Agent:** Answers clinic FAQs and rules using the supplied clinic policy context.
    *   **Emergency Agent:** Instantly escalates critical health situations without delay.
*   **Persistent Session Memory:** Contextual awareness across multi-turn conversations, allowing users to provide booking details naturally over time.
*   **Model Context Protocol (MCP):** Standardized, secure tool execution layer connecting the LLM to MongoDB for patient records.
*   **Live Activity Feed:** Workflow steps and tool activity in the UI.
*   **Voice Integration:** Manual push-to-talk voice input via browser SpeechRecognition API.
*   **Comprehensive Testing:** 5-layer evaluation suite including unit tests, integration tests, E2E scenarios, LLM-as-judge quality evaluations, and concurrency stress tests.

## System Architecture

```mermaid
graph TD
    User([User]) <--> Frontend[React/Vite UI]
    Frontend <--> API[FastAPI Backend]
    
    API --> Graph[LangGraph Orchestrator]
    
    Graph --> Triage[Triage Agent]
    
    Triage -->|Intent: Action| Action[Action Agent]
    Triage -->|Intent: Policy| Policy[Policy Agent]
    Triage -->|Intent: Emergency| Emergency[Emergency Agent]
    
    Action <--> MCP[MCP Server]
    MCP <--> DB[(MongoDB)]
    
    Policy <--> Knowledge[Verified passages from clinic_policies.md]
```

## Getting Started

### Prerequisites
*   Node.js v18+
*   Python 3.10+
*   MongoDB Atlas cluster (or local instance)
*   NVIDIA NIM API key

### 1. Environment Setup

Create a `.env` file in `backend/`:
```env
MONGODB_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
LITELLM_MODEL="openai/nvidia/nemotron-3.5-lightning-30b-a3b"
NVIDIA_API_KEY="your_api_key"
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt # (Requires fastapi, uvicorn, langgraph, litellm, pymongo, mcp)

# Run the server (runs on port 8001)
python main.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install

# Run the dev server (runs on port 5173)
npm run dev
```

## Testing and Evaluation

The repository contains the following test categories in `backend/tests/`. Their presence does not establish that live scenarios pass:

1.  **Unit Tests:** Tests MCP tools and routing logic in isolation using `mongomock`.
2.  **Integration Tests:** Validates session memory persistence and FastAPI endpoint contracts.
3.  **End-to-End Tests:** Tests full conversation flows (booking, cancelling, emergency) using the real LLM and MongoDB.
4.  **LLM Evaluation:** Uses an LLM-as-judge to score response quality (Accuracy, Empathy, Completeness, Safety).
5.  **Performance Tests:** Contains latency and concurrency checks; no deployed SLA is established.

Run tests using:
```bash
cd backend
python -m pytest tests/unit tests/integration -q
```

The legacy E2E tests call real services and can modify the configured clinic database;
they are excluded from the command above. Use the isolated evaluator for this project's
benchmark rather than running those tests against clinic records.

## Project Structure

```text
medibot/
├── backend/
│   ├── main.py              # FastAPI server & Session Store
│   ├── med_agents.py        # LangGraph definitions & Agent prompts
│   ├── med_mcp.py           # Model Context Protocol tools & MongoDB integration
│   ├── data/                # Knowledge base (clinic_policies.md)
│   └── tests/               # Unit, integration, and performance tests
├── frontend/
│   ├── src/                 # React UI components & push-to-talk voice
│   └── index.html           # Web app entry point
├── eval/
│   ├── run.py               # Unified evaluation runner & benchmark suite
│   ├── evaluator.py         # MCP-isolated agent evaluator
│   └── development.json     # 40-scenario clinical evaluation dataset
└── docs/
    ├── IEEE_EVALUATION_REPORT.md  # Formal peer-reviewed evaluation report
    ├── IEEE_DOCUMENTATION.md      # Full architecture specification
    ├── medibot_holdout.md         # Final 12 holdout conversation logs
    └── RESUME_EVIDENCE.md         # Recruiter evidence & test summary
```

## Résumé evidence

[Résumé evidence and verification](docs/RESUME_EVIDENCE.md) records the use case, engineering approach, test status, measured results, limits, and safe résumé wording.

The [public demo](https://medbot-backend-0895.onrender.com/) answered policy and emergency smoke prompts on 2026-10-22. Appointment actions need a separate live verification; see the evidence page for the failed pre-fix request and current limits.

## 📑 Clinical Evaluation & IEEE Benchmark Documentation

For the formal evaluation specification, benchmark methodology, mathematical formulations, and empirical clinical safety results, refer to:
👉 **[IEEE Clinical Evaluation Report](docs/IEEE_EVALUATION_REPORT.md)**

### Key Verified Metrics
- **AHRQ Emergency Severity Index (ESI) Triage Safety**: **100% Emergency Escalation Sensitivity (Recall = 1.000)** across Level 1/2 presentations with zero false negatives (0% triage leakage).
- **RAGAS Faithfulness & Grounding**: **0% Extrapolated Medical Claims** against clinic SOP context; 100% factual citation grounding on verified policy passages.
- **Workflow & Tool State Precision**: **97.5% Automated Conversation Pass Rate** (39/40 Dev Suite) and **100% Pass Rate** (12/12 Frozen Holdout Suite) with isolated MongoDB MCP state execution.
- **Inference Latency**: Sub-second deterministic emergency break (< 850ms) via LangGraph edge routing.

## Current agent evaluation framework

Use [eval/README.md](eval/README.md) for the unified 40-scenario development
evaluator, isolated real MCP-tool execution, explicit accuracy and unsupported-claim
measures, human quality review, and approved-feedback regression workflow.
This supports agent evaluation and a human-reviewed improvement loop. It does not
train an LLM, route between different models, or learn automatically from users.
Recorded metrics and evaluation coverage are documented in [eval/RESULTS.md](eval/RESULTS.md).

### Final evaluation results

The development suite improved from 34/40 to 39/40 conversations passing automated
checks. The frozen final suite passed 12/12 automated cases (14 user turns); human
review marked all 12 pass, with mean quality 4.75/5 and three noted completeness
omissions. These small-sample results do not establish universal accuracy or no
hallucinations. The feedback loop uses human-approved corrections and regression
cases; it does not train model weights automatically. See [full results and release
status](eval/RESULTS.md).

