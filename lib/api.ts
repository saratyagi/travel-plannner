import { ConversationMessage, PlannerEvent } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function* streamTripPlan(
  message: string,
  partialParams?: Record<string, unknown> | null,
  conversationHistory?: ConversationMessage[] | null,
): AsyncGenerator<PlannerEvent> {
  const body: Record<string, unknown> = { message };
  if (partialParams) body.partial_params = partialParams;
  if (conversationHistory) body.conversation_history = conversationHistory;

  const response = await fetch(`${API_BASE}/api/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') return;
      try {
        yield JSON.parse(payload) as PlannerEvent;
      } catch {
        // skip malformed lines
      }
    }
  }
}
