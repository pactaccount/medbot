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

  const [mobileTab, setMobileTab] = useState<'chat' | 'info'>('chat');

  useEffect(() => {
    gsap.fromTo(
      [navRef.current, ...Array.from(document.querySelectorAll('.panel-entrance'))],
      { opacity: 0, y: 20 },
      { opacity: 1, y: 0, stagger: 0.1, ease: 'power3.out', duration: 0.7, delay: 0.2 }
    );
  }, [mobileTab]);

  return (
    <div ref={bgRef} className="w-screen h-screen flex flex-col overflow-hidden font-sans bg-gray-50 text-slate-700">

      {/* ── Nav Bar ── */}
      <nav ref={navRef} className="flex-shrink-0 flex items-center justify-between px-4 sm:px-8 py-3 sm:py-4 border-b border-gray-200 bg-white/80 backdrop-blur-xl z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <span className="font-semibold text-slate-800 text-lg tracking-tight">MedBot</span>
          </div>
          <div className="h-5 w-px bg-gray-300 mx-1 sm:mx-2" />
          <span className="text-xs sm:text-sm text-slate-500 font-medium">Clinic Portal</span>
        </div>

        {/* Mobile Tab Switcher (< 1024px) */}
        <div className="flex lg:hidden items-center bg-gray-100 p-1 rounded-xl border border-gray-200 shadow-inner">
          <button
            type="button"
            onClick={() => setMobileTab('chat')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mobileTab === 'chat'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Assistant
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('info')}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              mobileTab === 'info'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            Clinic Info
          </button>
        </div>
      </nav>

      {/* ── Main Body ── */}
      <div className="flex-1 flex flex-col lg:flex-row items-center justify-center overflow-hidden px-3 sm:px-8">

        {/* ── Desktop: Left Info Panel / Mobile: Info Tab ── */}
        <div className={`panel-entrance w-full lg:w-[300px] h-[calc(100%-1rem)] lg:h-[calc(100%-4rem)] flex-shrink-0 py-2 sm:py-6 flex flex-col gap-4 ${
          mobileTab === 'info' ? 'flex' : 'hidden lg:flex'
        }`}>
          <InfoPanel agentState={agentState} activityLog={activityLog} />
        </div>

        {/* ── Desktop: Center Voice Visualizer ── */}
        <div className="hidden lg:flex flex-1 items-center justify-center panel-entrance min-w-[300px]">
          <VoiceVisualizer 
            isListening={isListening} 
            isSpeaking={isSpeaking} 
            onClick={() => toggleMicRef.current()}
          />
        </div>

        {/* ── Desktop: Right Chat Window / Mobile: Chat Tab ── */}
        <div className={`panel-entrance w-full lg:w-[400px] h-[calc(100%-1rem)] lg:h-[calc(100%-4rem)] flex-shrink-0 py-2 sm:py-6 flex flex-col ${
          mobileTab === 'chat' ? 'flex' : 'hidden lg:flex'
        }`}>
          {/* Mobile Voice Quick Orb */}
          <div className="flex lg:hidden items-center justify-between pb-2 mb-2 border-b border-gray-200/80 px-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Voice Receptionist</span>
            <button
              type="button"
              onClick={() => toggleMicRef.current()}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                isListening
                  ? 'bg-red-50 text-red-600 border-red-200 animate-pulse'
                  : isSpeaking
                  ? 'bg-blue-50 text-blue-600 border-blue-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isListening ? 'bg-red-500' : isSpeaking ? 'bg-blue-500' : 'bg-emerald-500'}`} />
              <span>{isListening ? 'Listening...' : isSpeaking ? 'Speaking...' : 'Tap for Voice'}</span>
            </button>
          </div>

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
