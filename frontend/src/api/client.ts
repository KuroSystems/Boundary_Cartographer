// ApiClient — the single adapter seam every view depends on (FE-01).
// fixtureClient serves contract/fixtures/*.json; httpClient POSTs/GETs the
// backend. Views never import one directly; they import from selectClient.

import type {
  ApprovalDecisionRequest,
  ApprovalState,
  HealthResponse,
  RunResponse,
  ScenarioResponse,
} from './types';

export interface ApiClient {
  getHealth(): Promise<HealthResponse>;
  getScenario(): Promise<ScenarioResponse>;
  createRun(scenarioId: string): Promise<RunResponse>;
  getRun(runId: string): Promise<RunResponse>;
  decideApproval(runId: string, req: ApprovalDecisionRequest): Promise<ApprovalState>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
