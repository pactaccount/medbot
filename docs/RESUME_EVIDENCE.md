# MedBot — résumé and demo evidence

## Problem and use case
Clinic reception involves routine policy questions, appointment actions, and urgent requests that need escalation. MedBot is a **workflow prototype** for routing those intents and calling appointment tools. It has no clinical validation and must not be presented as a diagnostic or compliant production system.

## Engineering approach
A LangGraph workflow triages requests, calls an LLM for policy or action handling, and uses an MCP server for MongoDB appointment operations. FastAPI serves the chat API and frontend. Session history carries context across turns. Appointment tool functions support lookup, booking, rescheduling, cancellation, and registration.

## Hard parts and changes
The MCP module previously constructed a MongoDB client during import, causing offline tests to attempt DNS resolution for a private database. It now connects on first tool use, which lets tests inject a mock collection. The action agent now uses an in-process MCP client rather than starting a second Python process per request on a small hosted instance. The frontend no longer substitutes fabricated responses when the server fails. A CORS test now sends a real preflight request. The default test command excludes explicitly marked external end-to-end cases; those still need a configured MongoDB and LLM.

## Verification and evidence
`cd backend && ./venv/bin/python -m pytest -q` passed **53 offline tests**, with **23 external-service cases deselected**, on 2026-10-22; the frontend production build passed. The [hosted smoke report](hosted_smoke_2026-10-22.json) records two successful synthetic requests (emergency and policy) and one failed appointment clarification before the MCP transport fix. The public [Render demo](https://medbot-backend-0895.onrender.com/) is reachable. These results do not measure clinical safety or prove booking completion. The repaired action path passed mocked tests but has not been reverified against the live appointment backend.

## Enterprise path and résumé wording
Before a hosted booking demo, use synthetic patients, lock down origins and access, add action confirmation, and run task-completion and unsafe-action evaluations. Current safe wording: “Built a LangGraph receptionist workflow with MCP appointment tools and 53 passing offline tests; verified hosted policy and emergency responses.” Do not claim booking success, health outcomes, or compliance.
