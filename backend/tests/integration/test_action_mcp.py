"""Exercise the actual in-process MCP transport without model or database calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from med_agents import action_agent


@pytest.mark.asyncio
async def test_action_clarification_lists_mcp_tools_without_subprocess():
    message = SimpleNamespace(content="Please share a date and patient ID.", tool_calls=[])
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    state = {
        "ticket_id": "mcp-smoke",
        "email_content": "I want to book an appointment.",
        "chat_history": [],
        "extracted_info": {},
        "steps": [],
    }
    with patch("med_agents.acompletion", new=AsyncMock(return_value=response)) as model:
        result = await action_agent(state)

    assert result["final_response"] == "Please share a date and patient ID."
    tool_names = {item["function"]["name"] for item in model.await_args.kwargs["tools"]}
    assert {"book_appointment", "cancel_appointment"} <= tool_names


@pytest.mark.asyncio
async def test_chat_reports_backend_failure_instead_of_fake_success():
    from httpx import ASGITransport, AsyncClient
    from main import app

    with patch("main.graph.ainvoke", new=AsyncMock(side_effect=RuntimeError("tool unavailable"))):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": "I need an appointment"})

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
