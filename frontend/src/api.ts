import { AgentState } from './types';

export type ApiResponse = {
  response: string;
  agentState: AgentState;
  session_id: string;
  steps: string[];
};

const EMERGENCY_KEYWORDS = ['chest pain', 'heart attack', 'stroke', 'emergency', 'can\'t breathe', 'unconscious', 'dying'];
const ACTION_KEYWORDS = ['book', 'cancel', 'reschedule', 'appointment', 'schedule', 'patient id', 'slot'];

// Maps backend intent strings -> frontend AgentState
const INTENT_TO_STATE: Record<string, AgentState> = {
  action:    'action',
  emergency: 'emergency',
  policy:    'policy',
  general:   'policy',
};

function detectScenario(message: string): AgentState {
  const lower = message.toLowerCase();
  if (EMERGENCY_KEYWORDS.some(k => lower.includes(k))) return 'emergency';
  if (ACTION_KEYWORDS.some(k => lower.includes(k))) return 'action';
  return 'triage';
}

// Persist session across turns so server-side memory works
let currentSessionId: string | null = null;

export async function sendMessage(userMessage: string): Promise<ApiResponse> {
  try {
    const API_BASE_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8001' : '');
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage, session_id: currentSessionId }),
      signal: AbortSignal.timeout(60000),  // 60s — LLM + MCP calls can take 20-40s
    });
    if (!res.ok) throw new Error(`Server error: ${res.status}`);
    const data = await res.json();

    // Persist session_id for next turn
    if (data.session_id) currentSessionId = data.session_id;

    const text: string = data.response || '';
    // Drive agentState from the real backend intent, fall back to client-side detection
    const agentState: AgentState = INTENT_TO_STATE[data.intent] ?? detectScenario(userMessage);

    return { response: text || 'The server returned an empty answer. Please retry.', agentState, session_id: data.session_id, steps: data.steps ?? [] };
  } catch {
    return {
      response: 'The clinic demo could not reach the server. No request was completed. Please retry.',
      agentState: 'triage',
      session_id: currentSessionId ?? '',
      steps: [],
    };
  }
}
