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

const MOCK_RESPONSES: Record<string, ApiResponse> = {
  triage: {
    response: 'Our clinic is open Monday–Friday 8am–6pm, Saturdays 9am–1pm. We accept BlueCross, Aetna, UnitedHealth, and most major insurers. Patients should fast for 8 hours prior to blood work appointments. Is there anything else I can help you with, or would you like to book a visit?',
    agentState: 'triage',
    session_id: '',
    steps: [],
  },
  policy: {
    response: 'Our clinic is open Monday–Friday 8am–6pm, Saturdays 9am–1pm. We accept BlueCross, Aetna, UnitedHealth, and most major insurers. Patients should fast for 8 hours prior to blood work appointments. Is there anything else I can help you with, or would you like to book a visit?',
    agentState: 'policy',
    session_id: '',
    steps: [],
  },
  action: {
    response: 'I can process that for you. Please provide your Patient ID, preferred date (YYYY-MM-DD), preferred time (HH:MM), and the reason for your visit, and I\'ll confirm availability instantly.',
    agentState: 'action',
    session_id: '',
    steps: [],
  },
  emergency: {
    response: '⚠️ EMERGENCY PROTOCOL ACTIVATED — This sounds like a life-threatening emergency. Please call 911 immediately or proceed to your nearest Emergency Room. Do not drive yourself. Stay on the line with emergency services.',
    agentState: 'emergency',
    session_id: '',
    steps: [],
  },
};

const delay = (ms: number) => new Promise(res => setTimeout(res, ms));

export async function sendMessage(userMessage: string): Promise<ApiResponse> {
  try {
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
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

    return { response: text || MOCK_RESPONSES[detectScenario(userMessage)].response, agentState, session_id: data.session_id, steps: data.steps ?? [] };
  } catch {
    return { ...MOCK_RESPONSES[detectScenario(userMessage)], session_id: currentSessionId ?? '' };
  }
}
