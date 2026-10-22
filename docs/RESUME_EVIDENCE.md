# MedBot — résumé and demo evidence

## Problem and use case
Clinic reception involves routine policy questions, appointment actions, and urgent requests that need escalation. MedBot is a **workflow prototype** for routing those intents and calling appointment tools. It has no clinical validation and must not be presented as a diagnostic or compliant production system.

## Engineering approach
A LangGraph workflow triages requests, calls an LLM for policy or action handling, and uses an MCP server for MongoDB appointment operations. FastAPI serves the chat API and frontend. Session history carries context across turns. Appointment tool functions support lookup, booking, rescheduling, cancellation, and registration.

## Hard parts and changes
The MCP module previously constructed a MongoDB client during import, causing offline tests to attempt DNS resolution for a private database. It now connects on first tool use, which lets tests inject a mock collection. A CORS test now sends a real preflight request. The default test command excludes explicitly marked external end-to-end cases; those still need a configured MongoDB and LLM.

## Verification and evidence
`cd backend && ./venv/bin/python -m pytest -q` passed **51 offline tests**, with **23 external-service cases deselected**, on 2026-10-22. This proves isolated tool, API, routing, and session behavior under mocks; it does not measure clinical safety or full hosted booking. The recorded Render backend URL timed out after 50 seconds. Link [the source and tests](https://github.com/pactaccount/medbot) until a synthetic-patient hosted flow is verified.

## Enterprise path and résumé wording
Before a hosted demo, use synthetic patients, lock down origins and access, add action confirmation, and run task-completion and unsafe-action evaluations. Current safe wording: “Built a LangGraph receptionist workflow with MCP appointment tools and 51 passing offline tests.” Do not claim health outcomes or compliance.
