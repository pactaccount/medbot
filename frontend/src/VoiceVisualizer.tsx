import React, { useRef, useEffect } from 'react';
import gsap from 'gsap';

type VoiceVisualizerProps = {
  isListening: boolean;
  isSpeaking: boolean;
  onClick: () => void;
};

export function VoiceVisualizer({ isListening, isSpeaking, onClick }: VoiceVisualizerProps) {
  const circleRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    // Kill any existing animations
    circleRefs.current.forEach(ref => {
      if (ref) gsap.killTweensOf(ref);
    });

    if (isListening || isSpeaking) {
      // Animate multiple circles to simulate voice pitches
      circleRefs.current.forEach((ref, index) => {
        if (!ref) return;
        
        const delay = index * 0.15;
        const duration = isSpeaking ? 0.6 : 0.4;
        const maxScale = isSpeaking ? 1.5 + index * 0.4 : 1.3 + index * 0.3;
        
        gsap.to(ref, {
          scale: maxScale,
          opacity: 0.1,
          duration: duration,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
          delay: delay
        });
      });
    } else {
      // Idle state
      circleRefs.current.forEach(ref => {
        if (!ref) return;
        gsap.to(ref, {
          scale: 1,
          opacity: 0.8,
          duration: 0.8,
          ease: "power2.out"
        });
      });
    }
  }, [isListening, isSpeaking]);

  return (
    <div 
      className="relative w-48 h-48 flex items-center justify-center cursor-pointer group"
      onClick={onClick}
      title={isListening ? "Stop listening" : "Start speaking"}
    >
      {/* 3 Rings for visualizer effect */}
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          ref={el => circleRefs.current[i] = el}
          className="absolute rounded-full bg-slate-400 mix-blend-multiply"
          style={{
            width: '100%',
            height: '100%',
            opacity: 0.8 - (i * 0.2),
            transform: 'scale(1)'
          }}
        />
      ))}
      
      {/* Core solid circle */}
      <div 
        className={`absolute rounded-full w-24 h-24 shadow-xl z-10 transition-colors duration-500 ${
          isListening ? 'bg-slate-300' : isSpeaking ? 'bg-slate-400' : 'bg-slate-200'
        }`} 
      />
    </div>
  );
}
