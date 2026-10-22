const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function getAuthToken(): string | null {
  return localStorage.getItem('readiness_token');
}

export function setAuthToken(token: string) {
  localStorage.setItem('readiness_token', token);
}

export function getHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(username: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error('Invalid credentials');
  const data = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function fetchAssets() {
  const res = await fetch(`${API_BASE}/assets`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load assets');
  return res.json();
}

export async function fetchWorkOrders(statusFilter?: string) {
  const url = statusFilter ? `${API_BASE}/workorders?status_filter=${statusFilter}` : `${API_BASE}/workorders`;
  const res = await fetch(url, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load work orders');
  return res.json();
}

export async function createWorkOrder(payload: any) {
  const res = await fetch(`${API_BASE}/workorders`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create work order');
  return res.json();
}

export async function submitWorkOrderResolution(workorderId: string, payload: any) {
  const res = await fetch(`${API_BASE}/workorders/${workorderId}/submit-resolution`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to submit resolution');
  return res.json();
}

export async function approveWorkOrder(workorderId: string, downtimeHours: number = 2.0, notes?: string) {
  const res = await fetch(`${API_BASE}/workorders/${workorderId}/approve`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ downtime_hours: downtimeHours, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Approval failed');
  }
  return res.json();
}

export async function rejectWorkOrder(workorderId: string, rejectionReason: string) {
  const res = await fetch(`${API_BASE}/workorders/${workorderId}/reject`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ rejection_reason: rejectionReason }),
  });
  if (!res.ok) throw new Error('Rejection failed');
  return res.json();
}

export async function fetchRecurringFaults() {
  const res = await fetch(`${API_BASE}/analytics/recurring`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load recurring faults');
  return res.json();
}

export async function fetchReadinessBoard() {
  const res = await fetch(`${API_BASE}/analytics/readiness`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load readiness board');
  return res.json();
}

export async function fetchAssetSubgraph(assetId: string) {
  const res = await fetch(`${API_BASE}/graph/subgraph/${assetId}`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load subgraph');
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`, { headers: getHeaders() });
  if (!res.ok) throw new Error('Failed to load metrics');
  return res.json();
}

export async function createTroubleshootingSession(payload: any) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to create session');
  return res.json();
}

export async function recordFinding(sessionId: string, payload: any) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/findings`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to record finding');
  return res.json();
}

export async function streamDiagnosis(
  payload: {
    asset_id: string;
    symptom_text: string;
    alarm_code?: string;
    observations?: string[];
  },
  callbacks: {
    onMetadata?: (data: any) => void;
    onChunk?: (text: string, timing: any) => void;
    onCards?: (cards: any[], audit: any[]) => void;
    onDone?: (timing: any) => void;
    onError?: (err: string) => void;
  }
) {
  const response = await fetch(`${API_BASE}/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, stream: true }),
  });

  if (!response.ok) {
    throw new Error(`Diagnosis request failed with HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('ReadableStream not supported');

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const block of lines) {
      if (!block.trim()) continue;
      const blockLines = block.split('\n');
      let eventType = '';
      let eventData = '';

      for (const line of blockLines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          eventData = line.slice(6).trim();
        }
      }

      if (eventData) {
        try {
          const parsed = JSON.parse(eventData);
          if (eventType === 'metadata') {
            callbacks.onMetadata?.(parsed);
          } else if (eventType === 'chunk') {
            callbacks.onChunk?.(parsed.text, parsed);
          } else if (eventType === 'cards') {
            callbacks.onCards?.(parsed.cards, parsed.audit);
          } else if (eventType === 'done') {
            callbacks.onDone?.(parsed);
          } else if (eventType === 'error') {
            callbacks.onError?.(parsed.error);
          }
        } catch (e) {
          console.error('Error parsing SSE chunk', e);
        }
      }
    }
  }
}
