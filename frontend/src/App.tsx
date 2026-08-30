import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import { AgentState } from './types';
import { InfoPanel } from './InfoPanel';
import { ChatWindow } from './ChatWindow';
import { VoiceVisualizer } from './VoiceVisualizer';

export default function App() {
  const [agentState, setAgentState] = useState<AgentState>('idle');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [toggleMicRef, setToggleMicRef] = useState<{ current: () => void }>({ current: () => {} });
  const [activityLog, setActivityLog] = useState<string[]>([]);

  const bgRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    gsap.fromTo(
      [navRef.current, ...Array.from(document.querySelectorAll('.panel-entrance'))],
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, stagger: 0.1, ease: 'power3.out', duration: 0.7, delay: 0.2 }
    );
  }, []);

  return (
    <div ref={bgRef} className="w-screen h-screen flex flex-col overflow-hidden font-sans bg-gray-50 text-slate-700">

      {/* ── Nav Bar ── */}
      <nav ref={navRef} className="flex-shrink-0 flex items-center justify-between px-8 py-4 border-b border-gray-200 bg-white/80 backdrop-blur-xl z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <span className="font-semibold text-slate-800 text-lg tracking-tight">MedBot</span>
          </div>
          <div className="h-5 w-px bg-gray-300 mx-2" />
          <span className="text-sm text-slate-500 font-medium">Clinic Portal</span>
        </div>
      </nav>

      {/* ── Main Body ── */}
      <div className="flex-1 flex items-center justify-center overflow-hidden px-8">

        {/* ── Left: Info Panel (300px fixed) ── */}
        <div className="panel-entrance w-[300px] h-[calc(100%-4rem)] flex-shrink-0 py-6 flex flex-col gap-4">
          <InfoPanel agentState={agentState} activityLog={activityLog} />
        </div>

        {/* ── Center: Voice Visualizer ── */}
        <div className="flex-1 flex items-center justify-center panel-entrance min-w-[300px]">
          <VoiceVisualizer 
            isListening={isListening} 
            isSpeaking={isSpeaking} 
            onClick={() => toggleMicRef.current()}
          />
        </div>

        {/* ── Right: Chat Window (400px fixed) ── */}
        <div className="panel-entrance w-[400px] h-[calc(100%-4rem)] flex-shrink-0 py-6 flex flex-col">
          <ChatWindow 
            agentState={agentState} 
            onStateChange={setAgentState} 
            isListening={isListening}
            setIsListening={setIsListening}
            isSpeaking={isSpeaking}
            setIsSpeaking={setIsSpeaking}
            registerToggleMic={(fn) => setToggleMicRef({ current: fn })}
            onActivityUpdate={setActivityLog}
          />
        </div>
      </div>
    </div>
  );
}
