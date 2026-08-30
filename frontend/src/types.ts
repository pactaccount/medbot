export type AgentState = 'idle' | 'triage' | 'policy' | 'action' | 'emergency';

export type Message = {
  id: string;
  sender: 'bot' | 'user';
  text: string;
  agentState?: AgentState;
  timestamp: number;
};

export type InfoTab = 'activity' | 'overview' | 'policies' | 'contact';

export const STATE_COLORS: Record<AgentState, string> = {
  idle:      '#94a3b8', // slate-400
  triage:    '#64748b', // slate-500
  policy:    '#0ea5e9', // sky-500
  action:    '#8b5cf6', // violet-500
  emergency: '#ef4444', // red-500
};

export const STATE_LABELS: Record<AgentState, string> = {
  idle:      'Idle — Core Consciousness Online',
  triage:    'Triage Agent — Analyzing Request…',
  policy:    'Policy Agent — Consulting Clinic Docs…',
  action:    'Action Agent — Executing Query…',
  emergency: 'Emergency Protocol — Escalating…',
};
