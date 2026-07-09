'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { AgentName, AgentState, Place } from '@/types';
import AgentProgress from '@/components/AgentProgress';
import TripReport from '@/components/TripReport';
import AttractionsSidebar from '@/components/AttractionsSidebar';
import { streamTripPlan } from '@/lib/api';

const DestinationGlobe = dynamic(() => import('@/components/DestinationGlobe'), { ssr: false });

const INITIAL_AGENTS: Record<AgentName, AgentState> = {
  orchestrator: { status: 'idle', message: '' },
  flight:       { status: 'idle', message: '' },
  hotel:        { status: 'idle', message: '' },
  budget:       { status: 'idle', message: '' },
  report:       { status: 'idle', message: '' },
};

type AppStatus = 'idle' | 'planning' | 'clarifying' | 'done' | 'error';
type PlanningPhase = 'globe' | 'plane' | null;

const EXAMPLE_TRIPS = [
  'I want to fly from New York to Tokyo for 10 days in August 2026, economy class, 2 travelers.',
  'Plan a trip from London to Paris, July 15–20 2026, 1 person, mid-range budget.',
  'Dubai to Bali, September 2026, 2 weeks, business class, luxury hotels, budget around $8000.',
];

const TODAY = new Date().toISOString().split('T')[0];

/** Extract destination from natural language before the backend replies. */
function extractDestination(text: string): string | null {
  // "from X to Y" → Y
  let m = text.match(/\bfrom\s+[\w\s]+?\s+to\s+([A-Z][A-Za-z\s]+?)(?=\s+for\b|\s+in\b|\s+on\b|\s+from\b|\s+,|,|\.|$)/i);
  if (m?.[1]?.trim()) return m[1].trim();

  // "trip/travel/fly/going/head to Y"
  m = text.match(/\b(?:trip|travel|fly(?:ing)?|going|head(?:ing)?|visit(?:ing)?|explore)\s+(?:from\s+\S+\s+)?to\s+([A-Z][A-Za-z\s]+?)(?=\s+for\b|\s+in\b|\s+on\b|\s+,|,|\.|$)/i);
  if (m?.[1]?.trim()) return m[1].trim();

  // plain "to Y" with capital letter
  m = text.match(/\bto\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?=\s+for\b|\s+in\b|\s+on\b|\s+,|,|\s+\d|\.| |$)/);
  if (m?.[1]?.trim()) return m[1].trim();

  // "X to Y" at start (e.g. "Dubai to Bali")
  m = text.match(/^([A-Za-z]+(?:\s[A-Za-z]+)?)\s+to\s+([A-Za-z]+(?:\s[A-Za-z]+)?)/i);
  if (m?.[2]?.trim()) return m[2].trim();

  return null;
}

export default function Home() {
  const [input, setInput] = useState('');
  // Upfront form fields — collected before submitting
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [travelers, setTravelers] = useState(2);

  const [status, setStatus] = useState<AppStatus>('idle');
  const [planningPhase, setPlanningPhase] = useState<PlanningPhase>(null);
  const [agents, setAgents] = useState<Record<AgentName, AgentState>>(INITIAL_AGENTS);
  const [report, setReport] = useState('');
  const [clarification, setClarification] = useState('');
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [clarificationMissingFields, setClarificationMissingFields] = useState<string[]>([]);
  const [partialParams, setPartialParams] = useState<Record<string, unknown> | null>(null);
  const [conversationHistory, setConversationHistory] = useState<string | null>(null);
  const [destination, setDestination] = useState<string | null>(null);
  const [places, setPlaces] = useState<Place[]>([]);
  const [attractionsLoading, setAttractionsLoading] = useState(false);
  const [error, setError] = useState('');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const clarificationRef = useRef<HTMLTextAreaElement>(null);
  const planningStartRef = useRef<number>(0);
  const showReportTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Globe phase automatically transitions to plane after 3 seconds
  useEffect(() => {
    if (planningPhase !== 'globe') return;
    const t = setTimeout(() => setPlanningPhase('plane'), 3000);
    return () => clearTimeout(t);
  }, [planningPhase]);

  const updateAgent = useCallback((agent: AgentName, update: Partial<AgentState>) => {
    setAgents((prev) => ({ ...prev, [agent]: { ...prev[agent], ...update } }));
  }, []);

  const runStream = useCallback(async (
    message: string,
    params?: Record<string, unknown> | null,
    history?: string | null,
  ) => {
    setStatus('planning');
    setPlanningPhase('globe');
    planningStartRef.current = Date.now();
    setAgents(INITIAL_AGENTS);
    setReport('');
    setClarification('');
    setError('');
    setPlaces([]);
    setAttractionsLoading(true);
    if (showReportTimerRef.current) clearTimeout(showReportTimerRef.current);

    try {
      for await (const event of streamTripPlan(message, params, history)) {
        switch (event.type) {
          case 'progress':
            updateAgent(event.agent, { status: event.status, message: event.message });
            break;

          case 'trip_params':
            if (event.data.destination) setDestination(event.data.destination);
            break;

          case 'clarification':
            setPlanningPhase(null);
            if (showReportTimerRef.current) clearTimeout(showReportTimerRef.current);
            setClarification(event.message);
            setClarificationMissingFields(event.missing_fields ?? []);
            setPartialParams(event.partial_params ?? null);
            setConversationHistory(event.conversation_history ?? null);
            setClarificationAnswer('');
            setStatus('clarifying');
            setTimeout(() => clarificationRef.current?.focus(), 50);
            return;

          case 'complete': {
            // Hold results until both animations have played (min 4.5 s: 3 s globe + 1.5 s plane)
            const elapsed = Date.now() - planningStartRef.current;
            const MIN_MS = 4500;
            const delay = Math.max(0, MIN_MS - elapsed);
            const reportText = event.report;
            showReportTimerRef.current = setTimeout(() => {
              setReport(reportText);
              setStatus('done');
              setPlanningPhase(null);
            }, delay);
            break;
          }

          case 'attractions':
            setPlaces(event.places ?? []);
            setAttractionsLoading(false);
            break;

          case 'error':
            setPlanningPhase(null);
            if (showReportTimerRef.current) clearTimeout(showReportTimerRef.current);
            setError(event.message);
            setAttractionsLoading(false);
            setStatus('error');
            return;
        }
      }
    } catch (err) {
      setPlanningPhase(null);
      if (showReportTimerRef.current) clearTimeout(showReportTimerRef.current);
      setError(err instanceof Error ? err.message : 'Unknown error. Is the backend running?');
      setStatus('error');
    } finally {
      setAttractionsLoading(false);
    }
  }, [updateAgent]);

  const handleSubmit = useCallback(() => {
    if (!input.trim() || status === 'planning') return;
    setConversationHistory(null);

    const detected = extractDestination(input.trim());
    setDestination(detected);

    // Pass upfront form values as partial params so the backend doesn't need to ask for them
    const partial: Record<string, unknown> = { travelers };
    if (startDate) partial.start_date = startDate;
    if (endDate) partial.end_date = endDate;
    setPartialParams(partial);

    runStream(input.trim(), partial);
  }, [input, startDate, endDate, travelers, status, runStream]);

  // Only show date pickers in clarification when dates are the sole hard-missing field.
  // When origin is also missing, show a text area so the user can answer both at once.
  const isDateClarification =
    clarificationMissingFields.includes('dates') &&
    !clarificationMissingFields.includes('origin');

  const handleClarificationSubmit = useCallback(() => {
    if (status === 'planning') return;
    if (isDateClarification) {
      if (!startDate || !endDate) return;
      runStream(`Departing ${startDate}, returning ${endDate}`, partialParams, conversationHistory);
    } else {
      if (!clarificationAnswer.trim()) return;
      runStream(clarificationAnswer.trim(), partialParams, conversationHistory);
    }
  }, [status, isDateClarification, startDate, endDate, clarificationAnswer, partialParams, conversationHistory, runStream]);

  const handleReset = () => {
    if (showReportTimerRef.current) clearTimeout(showReportTimerRef.current);
    setStatus('idle');
    setInput('');
    setClarificationAnswer('');
    setStartDate('');
    setEndDate('');
    setTravelers(2);
    setPlanningPhase(null);
    setAgents(INITIAL_AGENTS);
    setReport('');
    setClarification('');
    setClarificationMissingFields([]);
    setPartialParams(null);
    setConversationHistory(null);
    setDestination(null);
    setPlaces([]);
    setAttractionsLoading(false);
    setError('');
    textareaRef.current?.focus();
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <span className="text-2xl">🌍</span>
          <div>
            <h1 className="text-lg font-bold text-white">AI Travel Planner</h1>
            <p className="text-xs text-white/50">Multi-agent · Real-time search · Instant plan</p>
          </div>
          {status !== 'idle' && status !== 'planning' && (
            <button
              onClick={handleReset}
              className="ml-auto text-sm text-white/60 hover:text-white transition-colors"
            >
              ← New search
            </button>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-12">

        {/* ── IDLE ───────────────────────────────────────────────────── */}
        {status === 'idle' && (
          <div className="animate-fade-in">
            <div className="text-center mb-10">
              <h2 className="text-4xl font-bold text-white mb-3">Where do you want to go?</h2>
              <p className="text-white/60 text-lg">
                Describe your trip and our AI agents will find flights, hotels, and build your budget plan.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-6">
              {/* Destination / free-form text */}
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit();
                }}
                placeholder="E.g. I want to go from Mumbai to Paris — or just say 'Paris' and we'll ask the rest"
                className="w-full bg-transparent text-white placeholder-white/30 text-base resize-none outline-none min-h-[80px]"
                autoFocus
              />

              {/* ── Calendar: departure + return date pickers ────────── */}
              <div className="mt-4 pt-4 border-t border-white/10">
                <p className="text-white/40 text-xs mb-3">
                  Travel dates <span className="text-white/25">(optional — we&apos;ll ask if you skip)</span>
                </p>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-white/50 text-xs mb-1.5 block">Departure date</label>
                    <input
                      type="date"
                      value={startDate}
                      min={TODAY}
                      onChange={(e) => {
                        setStartDate(e.target.value);
                        if (endDate && e.target.value > endDate) setEndDate('');
                      }}
                      className="w-full bg-slate-800 border border-white/20 text-white rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-500 transition-colors cursor-pointer"
                      style={{ colorScheme: 'dark' }}
                    />
                  </div>
                  <div>
                    <label className="text-white/50 text-xs mb-1.5 block">Return date</label>
                    <input
                      type="date"
                      value={endDate}
                      min={startDate || TODAY}
                      onChange={(e) => setEndDate(e.target.value)}
                      className="w-full bg-slate-800 border border-white/20 text-white rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-500 transition-colors cursor-pointer"
                      style={{ colorScheme: 'dark' }}
                    />
                  </div>
                </div>
                {startDate && endDate && (
                  <p className="text-white/40 text-xs mt-2 text-center">
                    {Math.round(
                      (new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000
                    )}{' '}
                    nights
                  </p>
                )}
              </div>

              {/* ── Travelers counter + submit ────────────────────────── */}
              <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between flex-wrap gap-4">
                <div className="flex items-center gap-3">
                  <span className="text-white/50 text-sm">Travelers</span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setTravelers((n) => Math.max(1, n - 1))}
                      className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white text-lg font-semibold flex items-center justify-center transition-colors select-none"
                    >
                      −
                    </button>
                    <span className="text-white font-semibold text-lg w-7 text-center tabular-nums">
                      {travelers}
                    </span>
                    <button
                      type="button"
                      onClick={() => setTravelers((n) => Math.min(20, n + 1))}
                      className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 text-white text-lg font-semibold flex items-center justify-center transition-colors select-none"
                    >
                      +
                    </button>
                  </div>
                  <span className="text-white/40 text-sm">{travelers === 1 ? 'person' : 'people'}</span>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-white/30 text-xs hidden sm:block">Ctrl+Enter to submit</span>
                  <button
                    onClick={handleSubmit}
                    disabled={!input.trim()}
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-white/10 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm"
                  >
                    Plan My Trip →
                  </button>
                </div>
              </div>
            </div>

            {/* Example queries */}
            <div>
              <p className="text-white/40 text-xs mb-3 text-center">Try an example</p>
              <div className="grid gap-2">
                {EXAMPLE_TRIPS.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => { setInput(ex); textareaRef.current?.focus(); }}
                    className="text-left px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white/60 hover:text-white/90 text-sm transition-all"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ── PLANNING ───────────────────────────────────────────────── */}
        {status === 'planning' && (
          <div className="animate-fade-in">

            {/* PHASE 1 — Globe marks the destination (3 s) */}
            {planningPhase === 'globe' && (
              <div className="flex flex-col items-center justify-center min-h-[420px]">
                <p className="text-white/40 text-xs tracking-widest uppercase mb-2">Finding your destination</p>
                <p className="text-white/70 text-base italic mb-10 max-w-lg text-center line-clamp-2">
                  &ldquo;{input}&rdquo;
                </p>
                {destination && <DestinationGlobe destination={destination} />}
              </div>
            )}

            {/* PHASE 2 — Plane flies while agents work */}
            {planningPhase === 'plane' && (
              <div>
                {/* Plane + contrail + clouds */}
                <div className="relative w-full h-20 mb-8 overflow-hidden">
                  <div className="absolute inset-0 flex items-center">
                    {[10, 30, 55, 75, 90].map((left, i) => (
                      <div
                        key={i}
                        className="absolute text-white/10 text-4xl select-none"
                        style={{
                          left: `${left}%`,
                          top: `${20 + (i % 3) * 20}%`,
                          animation: `cloudDrift ${6 + i * 1.5}s linear infinite`,
                        }}
                      >
                        ☁
                      </div>
                    ))}
                  </div>
                  <div
                    className="absolute top-1/2 left-0 h-0.5 w-full"
                    style={{
                      background:
                        'linear-gradient(to right, transparent, rgba(147,197,253,0.3), transparent)',
                      animation: 'trailFade 3s ease-in-out infinite',
                    }}
                  />
                  <div
                    className="absolute top-1/2 -translate-y-1/2 text-4xl select-none"
                    style={{ animation: 'flyPlane 3s ease-in-out infinite' }}
                  >
                    ✈️
                  </div>
                </div>

                {/* Globe (still showing) + agent progress cards */}
                <div className="flex flex-col lg:flex-row gap-10 items-center lg:items-start justify-center">
                  {destination && (
                    <div className="flex-shrink-0">
                      <DestinationGlobe destination={destination} />
                    </div>
                  )}
                  <div className="flex-1 min-w-0 w-full">
                    <div className="mb-6">
                      <p className="text-white/50 text-sm mb-1 text-center lg:text-left">
                        Researching your trip
                      </p>
                      <p className="text-white/70 text-sm italic line-clamp-2 text-center lg:text-left">
                        &ldquo;{input}&rdquo;
                      </p>
                    </div>
                    <AgentProgress agents={agents} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── CLARIFYING ─────────────────────────────────────────────── */}
        {status === 'clarifying' && (
          <div className="animate-fade-in max-w-2xl mx-auto">
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-2xl p-8">
              <div className="flex items-start gap-4 mb-6">
                <span className="text-3xl flex-shrink-0">🤖</span>
                <div>
                  <h3 className="text-white font-semibold text-base mb-1">Quick question</h3>
                  <p className="text-white/80 text-sm leading-relaxed">{clarification}</p>
                </div>
              </div>

              {isDateClarification ? (
                <div className="space-y-4 mb-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-white/50 text-xs mb-1.5 block">Departure date</label>
                      <input
                        type="date"
                        value={startDate}
                        min={TODAY}
                        onChange={(e) => {
                          setStartDate(e.target.value);
                          if (endDate && e.target.value > endDate) setEndDate('');
                        }}
                        className="w-full bg-slate-800 border border-white/20 text-white rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-500 transition-colors cursor-pointer"
                        style={{ colorScheme: 'dark' }}
                      />
                    </div>
                    <div>
                      <label className="text-white/50 text-xs mb-1.5 block">Return date</label>
                      <input
                        type="date"
                        value={endDate}
                        min={startDate || TODAY}
                        onChange={(e) => setEndDate(e.target.value)}
                        className="w-full bg-slate-800 border border-white/20 text-white rounded-xl px-4 py-3 text-sm outline-none focus:border-blue-500 transition-colors cursor-pointer"
                        style={{ colorScheme: 'dark' }}
                      />
                    </div>
                  </div>
                  {startDate && endDate && (
                    <p className="text-white/40 text-xs text-center">
                      {Math.round(
                        (new Date(endDate).getTime() - new Date(startDate).getTime()) / 86400000
                      )}{' '}
                      nights
                    </p>
                  )}
                </div>
              ) : (
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-4">
                  <textarea
                    ref={clarificationRef}
                    value={clarificationAnswer}
                    onChange={(e) => setClarificationAnswer(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleClarificationSubmit();
                    }}
                    className="w-full bg-transparent text-white placeholder-white/30 text-sm resize-none outline-none min-h-[60px]"
                    placeholder="Type your answer here…"
                  />
                </div>
              )}

              <div className="flex items-center justify-between">
                <span className="text-white/30 text-xs">
                  {isDateClarification ? 'Select both dates to continue' : 'Ctrl+Enter to submit'}
                </span>
                <div className="flex gap-3">
                  <button
                    onClick={handleReset}
                    className="px-4 py-2 text-white/50 hover:text-white/80 text-sm transition-colors"
                  >
                    Start over
                  </button>
                  <button
                    onClick={handleClarificationSubmit}
                    disabled={
                      isDateClarification ? !startDate || !endDate : !clarificationAnswer.trim()
                    }
                    className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-white/10 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all text-sm"
                  >
                    Continue →
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── DONE ───────────────────────────────────────────────────── */}
        {status === 'done' && report && (
          <div className="flex gap-6 items-start">
            <div className="flex-1 min-w-0">
              <TripReport report={report} onReset={handleReset} />
            </div>
            <AttractionsSidebar
              destination={destination}
              places={places}
              loading={attractionsLoading}
            />
          </div>
        )}

        {/* ── ERROR ──────────────────────────────────────────────────── */}
        {status === 'error' && (
          <div className="animate-fade-in max-w-xl mx-auto text-center">
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8">
              <span className="text-4xl mb-4 block">⚠️</span>
              <h3 className="text-white font-semibold text-lg mb-2">Something went wrong</h3>
              <p className="text-white/60 text-sm mb-2">{error}</p>
              <p className="text-white/40 text-xs mb-6">
                Make sure the Python backend is running:{' '}
                <code className="text-white/60">uvicorn main:app --reload</code>
              </p>
              <button
                onClick={handleReset}
                className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl transition-all text-sm"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
