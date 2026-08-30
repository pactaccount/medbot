import os
import json
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated, List, Any
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from litellm import acompletion
import fitz # PyMuPDF
import litellm
import glob

# Resolve paths relative to this file so the server works from any CWD
_HERE = Path(__file__).parent          # medibot/backend/
POLICIES_PATH = _HERE / "data" / "clinic_policies.md"
PDF_DIR       = _HERE / "data"

# Set retry logic for intermittent high demand (503) errors
litellm.num_retries = 3
litellm.request_timeout = 60

# Ensure we have a model configured. Using Gemini by default.
os.environ.setdefault("LITELLM_MODEL", "gemini/gemini-3.5-flash")

class TicketState(TypedDict):
    ticket_id: str
    email_content: str
    messages: Annotated[list, add_messages]
    chat_history: list  # Plain [{"role": ..., "content": ...}] across all turns
    intent: str
    extracted_info: dict
    final_response: str
    steps: list  # Live activity log for the frontend feed

async def triage_agent(state: TicketState):
    print(f"[{state.get('ticket_id', 'Session')}] Triage Agent analyzing...")

    # Build conversation history context so follow-ups are classified correctly
    history = state.get("chat_history", [])
    history_text = ""
    if history:
        recent = history[-6:]  # last 3 turns
        history_text = "\n".join(
            f"{m.get('role','').capitalize()}: {m.get('content','')}"
            for m in recent if isinstance(m, dict)
        )

    prompt = f"""Analyze the following patient support conversation and classify the LATEST message intent.
    Intent must be exactly one of: 'policy', 'action', 'emergency', 'general'.
    - 'emergency': medical emergency (chest pain, bleeding, severe injury, trouble breathing).
    - 'action': booking, checking, cancelling, or rescheduling an appointment — INCLUDING follow-up messages that provide booking details (patient ID, date, time, reason) in an ongoing booking conversation.
    - 'policy': asking about rules, wait times, hours, insurance, or fasting.
    - 'general': anything else.

    Also extract any patient ID or email address if present in any message.
    Return JSON: {{"intent": "policy|action|emergency|general", "patient_id": "...", "email": "..."}}

    {f'Previous conversation:{chr(10)}{history_text}{chr(10)}' if history_text else ''}
    Latest patient message: {state['email_content']}
    """
    
    response = await acompletion(
        model=os.environ["LITELLM_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result_str = response.choices[0].message.content
    try:
        if result_str.startswith("```json"):
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        result = json.loads(result_str)
    except Exception as e:
        print(f"JSON Parse error: {e}, Content: {result_str}")
        result = {"intent": "general", "patient_id": None, "email": None}
        
    print(f"[{state.get('ticket_id', 'Session')}] Triage decided intent: {result.get('intent')}")
    return {
        "intent": result.get("intent", "general"),
        "extracted_info": result,
        "steps": state.get("steps", []) + [
            f"🔍 Triage Agent: Request received",
            f"🎯 Intent classified as '{result.get('intent', 'general')}'",
        ]
    }

async def emergency_agent(state: TicketState):
    return {
        "final_response": "This sounds like a medical emergency. Please call 911 immediately or go to the nearest emergency room.",
        "steps": state.get("steps", []) + ["🚨 Emergency Protocol activated — escalating to 911 advisory"]
    }

async def policy_agent(state: TicketState):
    print(f"[{state.get('ticket_id', 'Session')}] Policy Agent answering...")
    # Read policies.md and PDFs
    policies_text = ""
    try:
        with open(POLICIES_PATH, "r") as f:
            policies_text += f.read() + "\n\n"
    except FileNotFoundError:
        print(f"[PolicyAgent] WARNING: {POLICIES_PATH} not found")

    # Read PDFs from data folder
    pdf_files = list(PDF_DIR.glob("*.pdf"))[:3]  # Limit to 3 to save token context
    for pdf_file in pdf_files:
        try:
            doc = fitz.open(str(pdf_file))
            for page in doc:
                policies_text += page.get_text() + "\n"
        except Exception as e:
            print(f"Error reading PDF {pdf_file}: {e}")

    prompt = f"""You are the MedBot receptionist, a warm, empathetic, and highly professional human-like assistant.
    Answer the patient's request using ONLY the provided policies. 
    Speak conversationally and naturally. Avoid robotic bulleted lists unless absolutely necessary.
    Always be polite, caring, and helpful.
    
    Policies Context:
    {policies_text[:15000]} # Truncated to avoid context limits
    
    Patient Request:
    {state['email_content']}
    """
    
    response = await acompletion(
        model=os.environ["LITELLM_MODEL"],
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "final_response": response.choices[0].message.content,
        "steps": state.get("steps", []) + [
            f"📋 Policy Agent: Loaded clinic policies & {len(pdf_files)} PDF document(s)",
            "✅ Policy Agent: Response generated",
        ]
    }

async def action_agent(state: TicketState):
    print(f"[{state.get('ticket_id', 'Session')}] Action Agent investigating...")
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    import sys
    
    # Run the MCP server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["med_mcp.py"],
        env=dict(os.environ),
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            tools = tools_response.tools
            
            litellm_tools = []
            for t in tools:
                litellm_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })
            
            system_prompt = """You are the MedBot receptionist, a warm, empathetic, and highly professional medical assistant. 
Your goal is to help the patient by booking, cancelling, or checking their appointment using the provided tools.
CRITICAL INSTRUCTIONS:
- Speak conversationally and naturally, like a real human customer care representative. 
- DO NOT use bullet points or sound like a robot.
- Patient IDs can be ANY format the patient gives you (e.g. "23456", "P-1001", "JA-99") — do NOT reject them.
- The book_appointment tool creates the patient record automatically if they don't exist yet, so always proceed with booking.
- If you need to book for a new patient, pass their name in the patient_name field.
- If you are missing information to book an appointment (like patient ID, date, time, or reason for visit), ask for it gently one or two things at a time.
- Always be polite, caring, and helpful."""
            
            # Build messages from full conversation history so the LLM remembers earlier turns
            chat_history = state.get("chat_history", [])
            messages = [{"role": "system", "content": system_prompt}]

            # Replay all previous turns so the LLM has full context
            for m in chat_history:
                if isinstance(m, dict) and m.get("role") in ("user", "assistant"):
                    messages.append(m)

            # Append current user message as the latest turn
            messages.append({"role": "user", "content": state['email_content']})

            # Inject any triage-extracted info as a system hint
            if state.get('extracted_info'):
                messages.insert(1, {"role": "system", "content": f"Extracted info from triage: {json.dumps(state['extracted_info'])}"})
            response = await acompletion(
                model=os.environ["LITELLM_MODEL"],
                messages=messages,
                tools=litellm_tools
            )
            
            response_message = response.choices[0].message
            
            if getattr(response_message, 'tool_calls', None):
                messages.append(response_message.model_dump())
                for tool_call in response_message.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    print(f"[{state.get('ticket_id', 'Session')}] Calling tool {func_name} with {args}")
                    result = await session.call_tool(func_name, arguments=args)
                    
                    tool_content = str(result.content[0].text) if result.content else "Success"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": func_name,
                        "content": tool_content
                    })
                
                final_response = await acompletion(
                    model=os.environ["LITELLM_MODEL"],
                    messages=messages
                )
                return {
                    "final_response": final_response.choices[0].message.content,
                    "steps": state.get("steps", []) + [
                        f"⚙️ Action Agent: Connected to MCP tool server",
                        f"🔧 Tool called: {', '.join(tc.function.name for tc in response_message.tool_calls)}",
                        "✅ Action Agent: Task completed",
                    ]
                }
            else:
                return {
                    "final_response": response_message.content,
                    "steps": state.get("steps", []) + [
                        "⚙️ Action Agent: Processed request (no tool call needed)",
                    ]
                }

def route_ticket(state: TicketState) -> str:
    intent = state.get("intent", "").lower()
    if intent == "emergency":
        return "emergency_agent"
    elif intent == "policy":
        return "policy_agent"
    elif intent == "action":
        return "action_agent"
    else:
        return "policy_agent"

def build_graph():
    builder = StateGraph(TicketState)
    builder.add_node("triage_agent", triage_agent)
    builder.add_node("policy_agent", policy_agent)
    builder.add_node("action_agent", action_agent)
    builder.add_node("emergency_agent", emergency_agent)
    
    builder.set_entry_point("triage_agent")
    
    builder.add_conditional_edges(
        "triage_agent",
        route_ticket,
        {
            "policy_agent": "policy_agent",
            "action_agent": "action_agent",
            "emergency_agent": "emergency_agent"
        }
    )
    
    builder.add_edge("policy_agent", END)
    builder.add_edge("action_agent", END)
    builder.add_edge("emergency_agent", END)
    
    return builder.compile()
