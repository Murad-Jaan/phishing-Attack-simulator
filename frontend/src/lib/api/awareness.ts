export interface AwarenessRedFlag {
  label: string;
  explanation: string;
}

export interface AwarenessContent {
  simulation: boolean;
  red_flags: AwarenessRedFlag[];
}

export async function fetchAwareness(token: string): Promise<AwarenessContent> {
  const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const res = await fetch(
    `${api}/api/v1/awareness/${encodeURIComponent(token)}`,
    { cache: 'no-store' },
  );
  if (!res.ok) {
    throw new Error(`Awareness request failed with ${res.status}`);
  }
  const data = (await res.json()) as {
    simulation?: boolean;
    red_flags?: AwarenessRedFlag[];
  };
  return {
    simulation: data.simulation !== false,
    red_flags: Array.isArray(data.red_flags) ? data.red_flags : [],
  };
}
