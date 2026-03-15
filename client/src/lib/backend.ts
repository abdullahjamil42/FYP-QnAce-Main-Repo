type HealthResponse = {
  status: string;
  env: string;
  models: Record<string, string | null>;
};

function getApiUrl(): string {
  if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_QACE_API_URL) {
    return process.env.NEXT_PUBLIC_QACE_API_URL;
  }
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
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
