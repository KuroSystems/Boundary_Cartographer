// httpClient — talks to the backend over relative /api/v1 URLs (FE-01).
// In dev, vite.config.ts proxies /api to http://localhost:8000; browser code
// never hardcodes a host. Used when VITE_API_MODE=live.

import { ApiError, type ApiClient } from './client';
import type {
  ApprovalDecisionRequest,
  ApprovalState,
  HealthResponse,
  RunResponse,
  ScenarioResponse,
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    let code = 'UNKNOWN';
    let message = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as { error?: { code?: string; message?: string } };
      if (body.error) {
        code = body.error.code ?? code;
        message = body.error.message ?? message;
      }
    } catch {
      // non-JSON error body — keep defaults
    }
    throw new ApiError(res.status, code, message);
  }
  return (await res.json()) as T;
}

export const httpClient: ApiClient = {
  getHealth: () => request<HealthResponse>('/health'),
  getScenario: () => request<ScenarioResponse>('/scenarios/demo'),
  createRun: (scenarioId: string) =>
    request<RunResponse>('/runs', {
      method: 'POST',
      body: JSON.stringify({ scenario_id: scenarioId }),
    }),
  getRun: (runId: string) => request<RunResponse>(`/runs/${encodeURIComponent(runId)}`),
  decideApproval: (runId: string, req: ApprovalDecisionRequest) =>
    request<ApprovalState>(`/runs/${encodeURIComponent(runId)}/approval`, {
      method: 'POST',
      body: JSON.stringify(req),
    }),
};
