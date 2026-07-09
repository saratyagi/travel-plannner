'use client';

import { AgentName, AgentState } from '@/types';

const AGENTS: { key: AgentName; label: string; icon: string; desc: string }[] = [
  { key: 'orchestrator', label: 'Orchestrator', icon: '🧠', desc: 'Parsing your request' },
  { key: 'flight', label: 'Flight Agent', icon: '✈️', desc: 'Searching flights' },
  { key: 'hotel', label: 'Hotel Agent', icon: '🏨', desc: 'Searching hotels' },
  { key: 'budget', label: 'Budget Agent', icon: '💰', desc: 'Calculating estimates' },
  { key: 'report', label: 'Report Agent', icon: '📋', desc: 'Writing your plan' },
];

interface Props {
  agents: Record<AgentName, AgentState>;
}

export default function AgentProgress({ agents }: Props) {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-center text-white/70 text-sm font-medium mb-6 tracking-wider uppercase">
        Agents working on your trip
      </h2>
      <div className="space-y-3">
        {AGENTS.map(({ key, label, icon, desc }) => {
          const state = agents[key];
          const isDone = state.status === 'done';
          const isRunning = state.status === 'running';
          const isIdle = state.status === 'idle';

          return (
            <div
              key={key}
              className={`flex items-center gap-4 rounded-xl px-5 py-3 transition-all duration-500 ${
                isDone
                  ? 'bg-emerald-500/20 border border-emerald-500/30'
                  : isRunning
                  ? 'bg-blue-500/20 border border-blue-400/40'
                  : 'bg-white/5 border border-white/10'
              }`}
            >
              <span className="text-2xl">{icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`font-semibold text-sm ${
                      isDone
                        ? 'text-emerald-300'
                        : isRunning
                        ? 'text-blue-300'
                        : 'text-white/40'
                    }`}
                  >
                    {label}
                  </span>
                  {isRunning && (
                    <span className="flex gap-0.5">
                      {[0, 1, 2].map((i) => (
                        <span
                          key={i}
                          className="w-1 h-1 bg-blue-400 rounded-full animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }}
                        />
                      ))}
                    </span>
                  )}
                </div>
                <p className={`text-xs mt-0.5 truncate ${isIdle ? 'text-white/25' : 'text-white/60'}`}>
                  {state.message || desc}
                </p>
              </div>
              <div className="flex-shrink-0">
                {isDone && <span className="text-emerald-400 text-lg">✓</span>}
                {isRunning && (
                  <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                )}
                {isIdle && <div className="w-2 h-2 rounded-full bg-white/20" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
