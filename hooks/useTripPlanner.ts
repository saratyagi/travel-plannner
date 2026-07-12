'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { AgentName, AgentState, ConversationMessage, Place } from '@/types';
import { streamTripPlan } from '@/lib/api';
import { extractDestination } from '@/lib/utils';

export type AppStatus = 'idle' | 'planning' | 'clarifying' | 'done' | 'error';
export type PlanningPhase = 'globe' | 'plane' | null;

const TODAY = new Date().toISOString().split('T')[0];

const INITIAL_AGENTS: Record<AgentName, AgentState> = {
  orchestrator: { status: 'idle', message: '' },
  flight:       { status: 'idle', message: '' },
  hotel:        { status: 'idle', message: '' },
  budget:       { status: 'idle', message: '' },
  report:       { status: 'idle', message: '' },
};

export interface TripPlannerHandle {
  // form inputs
  input: string;
  setInput: (v: string) => void;
  startDate: string;
  setStartDate: (v: string) => void;
  endDate: string;
  setEndDate: (v: string) => void;
  travelers: number;
  setTravelers: React.Dispatch<React.SetStateAction<number>>;
  // app state (read-only)
  status: AppStatus;
  planningPhase: PlanningPhase;
  agents: Record<AgentName, AgentState>;
  report: string;
  clarification: string;
  clarificationAnswer: string;
  setClarificationAnswer: (v: string) => void;
  clarificationMissingFields: string[];
  destination: string | null;
  places: Place[];
  attractionsLoading: boolean;
  error: string;
  // derived
  isDateClarification: boolean;
  today: string;
  // handlers
  handleSubmit: () => void;
  handleClarificationSubmit: () => void;
  handleReset: () => void;
  // refs
  textareaRef: React.RefObject<HTMLTextAreaElement>;
  clarificationRef: React.RefObject<HTMLTextAreaElement>;
}

export function useTripPlanner(): TripPlannerHandle {
  const [input, setInput] = useState('');
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
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[] | null>(null);
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
    history?: ConversationMessage[] | null,
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

    const partial: Record<string, unknown> = { travelers };
    if (startDate) partial.start_date = startDate;
    if (endDate) partial.end_date = endDate;
    setPartialParams(partial);

    runStream(input.trim(), partial);
  }, [input, startDate, endDate, travelers, status, runStream]);

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

  const handleReset = useCallback(() => {
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
  }, []);

  return {
    input, setInput,
    startDate, setStartDate,
    endDate, setEndDate,
    travelers, setTravelers,
    status, planningPhase, agents,
    report,
    clarification,
    clarificationAnswer, setClarificationAnswer,
    clarificationMissingFields,
    destination, places, attractionsLoading,
    error,
    isDateClarification,
    today: TODAY,
    handleSubmit, handleClarificationSubmit, handleReset,
    textareaRef, clarificationRef,
  };
}
