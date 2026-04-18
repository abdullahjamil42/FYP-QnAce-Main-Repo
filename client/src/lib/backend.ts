type HealthResponse = {
  status: string;
  env: string;
  models: Record<string, string | null>;
};

export type CoachingRequest = {
  mode: string;
  difficulty: string;
  duration_minutes: number;
  content_score: number;
  delivery_score: number;
  composure_score: number;
  final_score: number;
  transcript_texts: string[];
  vocal_emotion?: string;
  face_emotion?: string;
};

export function getApiUrl(): string {
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_QACE_API_URL) {
    return process.env.NEXT_PUBLIC_QACE_API_URL;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
}

/**
 * Stream AI coaching feedback for a completed session.
 * Calls the backend SSE endpoint and yields text chunks as they arrive.
 * Automatically handles adapter swap (evaluator → coach → evaluator) on the backend.
 */
export async function* streamCoaching(request: CoachingRequest): AsyncGenerator<string> {
  const response = await fetch(`${getApiUrl()}/coaching/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Coaching request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6);
      if (data === "[DONE]") return;
      // Unescape newlines encoded by the server
      yield data.replace(/\\n/g, "\n");
    }
  }
}

export async function fetchBackendHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${getApiUrl()}/health`, {
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}
