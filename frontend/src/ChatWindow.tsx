import React, { useState, useRef, useEffect, useCallback } from 'react';
import gsap from 'gsap';
import ReactMarkdown from 'react-markdown';
import { AgentState, Message, STATE_COLORS } from './types';
import { sendMessage } from './api';

const QUICK_PROMPTS = [
  { label: 'Book Appointment',    text: 'I\'d like to book an appointment'      },
  { label: 'Fasting Policy',      text: 'Do I need to fast before blood work?'  },
  { label: 'Cancel Appointment',  text: 'I need to cancel my appointment'       },
];

type ChatWindowProps = {
  agentState: AgentState;
  onStateChange: (state: AgentState) => void;
  isListening: boolean;
  setIsListening: (val: boolean) => void;
  isSpeaking: boolean;
  setIsSpeaking: (val: boolean) => void;
  registerToggleMic: (fn: () => void) => void;
  onActivityUpdate: (steps: string[]) => void;
};

export function ChatWindow({ 
  agentState, onStateChange, 
  isListening, setIsListening,
  isSpeaking, setIsSpeaking,
  registerToggleMic,
  onActivityUpdate
}: ChatWindowProps) {
  const [messages, setMessages] = useState<Message[]>([{
    id: '0',
    sender: 'bot',
    text: 'Hello. I\'m your MedBot Receptionist. I can book appointments, or answer clinic questions. How may I assist you today?',
    agentState: 'idle',
    timestamp: Date.now(),
  }]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const feedRef  = useRef<HTMLDivElement>(null);
  const endRef   = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recogRef = useRef<any>(null);
  const inputStrRef = useRef<string>(input);
  
  // Keep the ref up to date for the microphone callback
  useEffect(() => {
    inputStrRef.current = input;
  }, [input]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!panelRef.current) return;
    const color = STATE_COLORS[agentState];
    if (agentState !== 'idle') {
      gsap.to(panelRef.current, {
        boxShadow: `0 0 0 1.5px ${color}60, 0 0 28px ${color}28, 0 8px 32px rgba(0,0,0,0.04)`,
        duration: 0.5,
        ease: 'power2.out',
        repeat: agentState === 'emergency' ? -1 : 0,
        yoyo: true,
      });
    } else {
      gsap.killTweensOf(panelRef.current, 'boxShadow');
      gsap.to(panelRef.current, {
        boxShadow: '0 0 0 1px rgba(226, 232, 240, 1), 0 8px 32px rgba(0,0,0,0.03)',
        duration: 0.8,
        ease: 'power2.out',
      });
    }
  }, [agentState]);

  const speak = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.replace(/⚠️\s*/g, ''));
    u.rate  = 1.05;
    u.pitch = 1.0;
    
    u.onstart = () => setIsSpeaking(true);
    u.onend   = () => setIsSpeaking(false);
    u.onerror = () => setIsSpeaking(false);

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Samantha') || v.name.includes('Karen') ||
      v.name.includes('Google US English') || v.name.includes('Moira')
    );
    if (preferred) u.voice = preferred;
    window.speechSynthesis.speak(u);
  }, [setIsSpeaking]);

  const submit = useCallback(async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: text.trim(), timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    onStateChange('triage');

    try {
      const { response, agentState: nextState, steps } = await sendMessage(text.trim());

      // Push activity steps to InfoPanel
      if (steps && steps.length > 0) onActivityUpdate(steps);

      if (nextState === 'action') {
        onStateChange('action');
        await new Promise(r => setTimeout(r, 400));
      } else {
        onStateChange(nextState);
      }

      const botMsg: Message = {
        id: `${Date.now()}_bot`,
        sender: 'bot',
        text: response,
        agentState: nextState,
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, botMsg]);
      speak(response);

      setTimeout(() => onStateChange('idle'), nextState === 'emergency' ? 10000 : 5000);
    } catch {
      onStateChange('idle');
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isLoading, onStateChange, speak]);

  const toggleMic = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert('Speech recognition unavailable in this browser.'); return; }

    // STOP LISTENING & SUBMIT
    if (isListening) {
      recogRef.current?.stop();
      setIsListening(false);
      
      // Auto-submit if there is text
      if (inputStrRef.current.trim()) {
        submit(inputStrRef.current);
      }
      return;
    }
    
    // START LISTENING (CONTINUOUS)
    const rec = new SR();
    recogRef.current = rec;
    rec.continuous      = true;
    rec.interimResults  = true;
    rec.lang            = 'en-US';

    rec.onstart  = () => setIsListening(true);
    rec.onerror  = () => setIsListening(false);

    // When browser fires onend (silence/timeout), just reset UI — user submits manually by clicking the circle again
    rec.onend    = () => {
      setIsListening(false);
    };

    rec.onresult = (e: any) => {
      let finalTranscript = '';
      for (let i = e.resultIndex; i < e.results.length; ++i) {
        if (e.results[i].isFinal) {
          finalTranscript += e.results[i][0].transcript;
        } else {
          finalTranscript += e.results[i][0].transcript;
        }
      }
      // Just replacing the input with the full transcript for the current session is easiest
      const t = Array.from(e.results).map((r: any) => r[0].transcript).join('');
      setInput(t);
    };
    rec.start();
  }, [isListening, setIsListening, submit]);

  // Register toggleMic with App.tsx
  useEffect(() => {
    registerToggleMic(toggleMic);
  }, [registerToggleMic, toggleMic]);

  return (
    <div
      ref={panelRef}
      className="bg-white rounded-2xl flex flex-col h-full overflow-hidden transition-all duration-700 border border-slate-200 shadow-sm"
    >
      {/* ── Header ── */}
      <div className="px-5 py-4 border-b border-slate-100 flex-shrink-0 bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            M
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800 leading-none">Assistant</p>
            <p className="text-[10px] font-mono mt-1 text-slate-500">
              {isLoading ? 'Thinking…' : isSpeaking ? 'Speaking…' : isListening ? '🎤 Listening…' : 'Online'}
            </p>
          </div>
        </div>
      </div>

      {/* ── Message Feed ── */}
      <div ref={feedRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 no-scrollbar bg-white">
        {messages.length === 1 && (
          <div className="mb-4">
            <div className="flex flex-col gap-2">
              {QUICK_PROMPTS.map(p => (
                <button
                  key={p.label}
                  onClick={() => submit(p.text)}
                  className="text-left text-xs px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-100 transition-all duration-200"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble key={msg.id} msg={msg} isLatest={idx === messages.length - 1} />
        ))}

        {isLoading && (
          <div className="flex items-end gap-2">
            <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">M</div>
            <div className="bg-slate-50 border border-slate-100 rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1">
              {[0, 160, 320].map((d, i) => (
                <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* ── Input Bar ── */}
      <div className="px-4 py-3 border-t border-slate-100 bg-white flex-shrink-0">
        <div className="flex items-center gap-2">
          {/* Removed old small mic button; center circle now acts as mic control */}
          
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit(input)}
            placeholder={isListening ? 'Listening…' : 'Type a message…'}
            disabled={isLoading}
            className="flex-1 text-sm text-slate-800 placeholder-slate-400 border border-slate-200 rounded-full px-4 py-2 focus:outline-none focus:border-slate-400 transition-all duration-300 disabled:opacity-50 bg-slate-50"
          />

          <button
            onClick={() => submit(input)}
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-slate-800 text-white hover:bg-slate-700 transition-all duration-300 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg, isLatest }: { msg: Message; isLatest: boolean }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !isLatest) return;
    gsap.fromTo(ref.current, { opacity: 0, y: 10 }, { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' });
  }, [isLatest]);

  return (
    <div ref={ref} className={`flex items-end gap-2 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
      {msg.sender === 'bot' && (
        <div className="w-6 h-6 rounded-full bg-slate-800 flex-shrink-0 flex items-center justify-center text-white text-[9px] font-bold mb-0.5">M</div>
      )}
      <div
        className="max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
        style={
          msg.sender === 'user'
            ? { background: '#1e293b', color: '#f8fafc', borderRadius: '18px 18px 4px 18px' }
            : { background: '#f8fafc', border: '1px solid #f1f5f9', color: '#334155', borderRadius: '18px 18px 18px 4px' }
        }
      >
        {msg.sender === 'bot' ? (
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-4 mb-1 space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-4 mb-1 space-y-0.5">{children}</ol>,
              li: ({ children }) => <li className="text-sm">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold text-slate-800">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
            }}
          >
            {msg.text}
          </ReactMarkdown>
        ) : (
          msg.text
        )}
      </div>
    </div>
  );
}
