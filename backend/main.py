from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from med_agents import build_graph
from typing import Optional
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

import os

frontend_url = os.environ.get("FRONTEND_URL")
origins = ["*"]
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph()

# In-memory session store: maps session_id -> chat_history (plain {role, content} dicts)
SESSION_STORE: dict[str, list] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    intent: str  # The actual intent decided by the triage agent
    steps: list[str] = []  # Live activity log for the frontend feed

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())

    # Rehydrate chat_history for this session (plain user/assistant dicts)
    chat_history = SESSION_STORE.get(session_id, [])

    initial_state = {
        "ticket_id": session_id,
        "email_content": request.message,
        "messages": [],          # LangGraph messages (unused for memory)
        "chat_history": chat_history,  # Our actual conversation history
        "intent": "",
        "extracted_info": {},
        "final_response": "",
        "steps": []
    }

    intent = "general"
    final_state = initial_state  # fallback if graph errors
    try:
        final_state = await graph.ainvoke(initial_state)
        response_text = final_state.get("final_response", "I'm sorry, I encountered an error processing your request.")
        intent = final_state.get("intent", "general")

        # Append this turn to chat_history and persist for next turn
        updated_history = chat_history + [
            {"role": "user",      "content": request.message},
            {"role": "assistant", "content": response_text},
        ]
        SESSION_STORE[session_id] = updated_history

    except Exception as e:
        print(f"Error in graph: {e}")
        import traceback; traceback.print_exc()
        response_text = "I encountered an internal error. Please try again later."

    return ChatResponse(
        response=response_text,
        session_id=session_id,
        intent=intent,
        steps=final_state.get("steps", [])
    )

# --- Serve React Frontend ---
frontend_dist_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist_path.exists():
    # Mount the assets directory explicitly
    assets_dir = frontend_dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        file_path = frontend_dist_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist_path / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
