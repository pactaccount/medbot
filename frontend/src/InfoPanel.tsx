import React, { useState, useRef, useEffect } from 'react';
import gsap from 'gsap';
import { InfoTab, AgentState, STATE_COLORS, STATE_LABELS } from './types';

const TABS: { id: InfoTab; label: string }[] = [
  { id: 'activity',  label: 'Activity'        },
  { id: 'overview',  label: 'Overview'        },
  { id: 'policies',  label: 'Policies & FAQs' },
  { id: 'contact',   label: 'Clinic Contact'  },
];

type InfoPanelProps = {
  agentState: AgentState;
  activityLog: string[];
};

export function InfoPanel({ agentState, activityLog }: InfoPanelProps) {
  const [activeTab, setActiveTab] = useState<InfoTab>('activity');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const accentColor = STATE_COLORS[agentState];

  // Auto-switch to Activity tab when new steps arrive and agent is active
  useEffect(() => {
    if (activityLog.length > 0 && agentState !== 'idle') {
      setActiveTab('activity');
    }
  }, [activityLog, agentState]);

  const handleTabChange = (tab: InfoTab) => {
    if (!contentRef.current) { setActiveTab(tab); return; }
    gsap.to(contentRef.current, {
      opacity: 0, y: 6, duration: 0.15, ease: 'power2.in',
      onComplete: () => {
        setActiveTab(tab);
        gsap.to(contentRef.current, { opacity: 1, y: 0, duration: 0.22, ease: 'power2.out' });
      }
    });
  };

  const toggleCollapse = () => {
    if (!wrapperRef.current) return;
    const nextCollapsed = !isCollapsed;
    setIsCollapsed(nextCollapsed);
    
    // Fix: Instead of height: 'auto', explicitly clear height after expansion
    if (nextCollapsed) {
      gsap.to(wrapperRef.current, { height: 0, opacity: 0, duration: 0.35, ease: 'power2.inOut' });
    } else {
      gsap.set(wrapperRef.current, { height: 'auto' });
      gsap.from(wrapperRef.current, { height: 0, opacity: 0, duration: 0.35, ease: 'power2.inOut' });
      gsap.to(wrapperRef.current, { opacity: 1, duration: 0.35 });
    }
  };

  return (
    <div
      className="glass-panel flex flex-col overflow-hidden transition-all duration-700"
      style={{ borderColor: `${accentColor}22` }}
    >
      {/* ── Panel Header ── */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-2 h-2 rounded-full bg-slate-500" />
            {agentState !== 'idle' && (
              <div className="absolute inset-0 rounded-full animate-ping opacity-60 bg-slate-500" />
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-700 tracking-wide">MedBot Clinical System</p>
            <p className="text-[10px] font-mono text-slate-500 transition-colors duration-500">
              {STATE_LABELS[agentState]}
            </p>
          </div>
        </div>
        <button
          onClick={toggleCollapse}
          className="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded z-10 relative cursor-pointer"
        >
          <svg
            className={`w-4 h-4 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {/* ── Tabs & Content Wrapper ── */}
      <div ref={wrapperRef} className="overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-white/10 px-2 pt-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`px-4 py-2 text-xs font-medium tracking-wide transition-all duration-200 border-b-2 -mb-px ${
                activeTab === tab.id
                  ? 'border-slate-600 text-slate-700'
                  : 'border-transparent text-slate-400 hover:text-slate-600'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div ref={contentRef} className="p-5 overflow-y-auto no-scrollbar max-h-[60vh]">
          {activeTab === 'activity'  && <ActivityTab activityLog={activityLog} agentState={agentState} />}
          {activeTab === 'overview'  && <OverviewTab />}
          {activeTab === 'policies'  && <PoliciesTab />}
          {activeTab === 'contact'   && <ContactTab  />}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────
// Tab Content Components
// ────────────────────────────────

function ActivityTab({ activityLog, agentState }: { activityLog: string[]; agentState: AgentState }) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!listRef.current) return;
    const items = listRef.current.querySelectorAll('.step-item');
    gsap.fromTo(
      items,
      { opacity: 0, x: -8 },
      { opacity: 1, x: 0, stagger: 0.07, duration: 0.25, ease: 'power2.out' }
    );
  }, [activityLog]);

  const accentColor = STATE_COLORS[agentState];

  if (activityLog.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
        <div className="w-8 h-8 rounded-full border-2 border-dashed border-slate-200 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-slate-300 animate-pulse" />
        </div>
        <p className="text-xs text-slate-400 font-mono">Awaiting next request…</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5" ref={listRef}>
      <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mb-3">Agent Activity Log</p>
      {activityLog.map((step, i) => (
        <div
          key={i}
          className="step-item flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-50 border border-slate-100"
        >
          <div
            className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5"
            style={{ backgroundColor: accentColor }}
          />
          <span className="text-xs text-slate-600 leading-relaxed">{step}</span>
        </div>
      ))}
    </div>
  );
}

function OverviewTab() {
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-600 leading-relaxed font-medium">
        Welcome to the MedBot Clinic Portal. This intelligent assistant is designed to help you quickly navigate clinic services.
      </p>
      <div className="bg-slate-50/80 border border-slate-100 rounded-lg p-4 mt-4">
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mb-2">Capabilities</h3>
        <ul className="text-xs text-slate-600 space-y-2 list-disc pl-4">
          <li>Instantly book, cancel, or reschedule appointments.</li>
          <li>Query fasting guidelines and clinic policies.</li>
          <li>Escalate urgent medical symptoms.</li>
          <li>Voice-enabled, hands-free assistance.</li>
        </ul>
      </div>
    </div>
  );
}

function PoliciesTab() {
  const faqs = [
    { q: 'How early should I arrive?', a: 'Please arrive 10–15 minutes before your scheduled time to complete any necessary paperwork.' },
    { q: 'Do I need to fast before a blood test?', a: 'Yes. For most blood work, you must fast for a minimum of 8 hours. Water and prescribed medications are permitted.' },
    { q: 'What is the cancellation policy?', a: 'Appointments can be cancelled up to 24 hours in advance at no charge. Late cancellations may incur a fee.' },
    { q: 'Which insurance plans do you accept?', a: 'We accept BlueCross BlueShield, Aetna, UnitedHealth, Cigna, and Medicare. Please bring your insurance card.' },
  ];

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mb-3">Clinical Policies</p>
      {faqs.map((faq, i) => (
        <details key={i} className="group border border-slate-200/60 rounded-lg overflow-hidden bg-white/50">
          <summary className="flex items-center justify-between px-3 py-2.5 cursor-pointer text-xs font-medium text-slate-700 hover:bg-slate-50/80 list-none transition-colors">
            {faq.q}
            <svg className="w-3.5 h-3.5 text-slate-400 group-open:rotate-180 transition-transform flex-shrink-0 ml-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </summary>
          <div className="px-3 pb-3 pt-1 text-xs text-slate-500 leading-relaxed border-t border-slate-100 bg-slate-50/50">
            {faq.a}
          </div>
        </details>
      ))}
    </div>
  );
}

function ContactTab() {
  const contacts = [
    { icon: '📍', label: 'Address',   value: '1200 Medical Plaza Dr, Suite 400\nSan Francisco, CA 94103' },
    { icon: '📞', label: 'Phone',     value: '(415) 555-0192' },
    { icon: '✉️', label: 'Email',     value: 'reception@medbot.clinic' },
    { icon: '🕒', label: 'Hours',     value: 'Mon–Fri: 8:00am – 6:00pm\nSaturday: 9:00am – 1:00pm' },
  ];

  return (
    <div className="space-y-3">
      <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mb-3">Clinic Contact</p>
      {contacts.map(c => (
        <div key={c.label} className="flex gap-3 p-3 border border-slate-200/60 rounded-lg bg-white/50">
          <span className="text-base leading-none mt-0.5">{c.icon}</span>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-widest text-slate-400 mb-0.5">{c.label}</p>
            <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-line">{c.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
