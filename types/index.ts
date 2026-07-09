export type AgentName = 'orchestrator' | 'flight' | 'hotel' | 'budget' | 'report';
export type AgentStatus = 'idle' | 'running' | 'done' | 'error';

export interface ProgressEvent {
  type: 'progress';
  agent: AgentName;
  status: 'running' | 'done';
  message: string;
}

export interface TripParamsEvent {
  type: 'trip_params';
  data: {
    origin: string;
    destination: string;
    start_date: string;
    end_date: string;
    travelers: number;
    cabin_class: string;
    hotel_pref: string;
    budget_ceiling_usd: number | null;
  };
}

export interface ClarificationEvent {
  type: 'clarification';
  clarification_type: 'hard' | 'soft';
  message: string;
  missing_fields: string[];
  partial_params: Record<string, unknown>;
  conversation_history: string;
}

export interface Place {
  name: string;
  category: string;
  description: string;
  estimated_cost_usd: number;
  cost_note: string;
  image_url: string | null;
}

export interface CompleteEvent {
  type: 'complete';
  report: string;
}

export interface AttractionsEvent {
  type: 'attractions';
  places: Place[];
}

export interface ErrorEvent {
  type: 'error';
  message: string;
}

export type PlannerEvent =
  | ProgressEvent
  | TripParamsEvent
  | ClarificationEvent
  | CompleteEvent
  | AttractionsEvent
  | ErrorEvent;

export interface AgentState {
  status: AgentStatus;
  message: string;
}
