"""
Layer 1 — Unit Tests: Routing Logic
Tests the route_ticket() function in isolation — no LLM, no DB.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from med_agents import route_ticket


class TestRouteTicket:
    """All tests call route_ticket() with a minimal state dict."""

    def _state(self, intent: str):
        return {
            "ticket_id": "test",
            "email_content": "test",
            "messages": [],
            "chat_history": [],
            "intent": intent,
            "extracted_info": {},
            "final_response": "",
            "steps": [],
        }

    def test_routes_emergency(self):
        assert route_ticket(self._state("emergency")) == "emergency_agent"

    def test_routes_action(self):
        assert route_ticket(self._state("action")) == "action_agent"

    def test_routes_policy(self):
        assert route_ticket(self._state("policy")) == "policy_agent"

    def test_routes_general_to_policy(self):
        """'general' intent falls back to policy agent."""
        assert route_ticket(self._state("general")) == "policy_agent"

    def test_routes_empty_string_to_policy(self):
        assert route_ticket(self._state("")) == "policy_agent"

    def test_routes_unknown_intent_to_policy(self):
        assert route_ticket(self._state("banana")) == "policy_agent"

    def test_routes_case_insensitive_emergency(self):
        assert route_ticket(self._state("EMERGENCY")) == "emergency_agent"

    def test_routes_case_insensitive_action(self):
        assert route_ticket(self._state("ACTION")) == "action_agent"

    def test_routes_mixed_case_policy(self):
        assert route_ticket(self._state("Policy")) == "policy_agent"
