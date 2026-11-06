// fixtureClient — serves the frozen contract fixtures directly (FE-01/FE-02).
// Used when VITE_API_MODE=fixture (the default): no backend required.
// Fixtures are validated against the Zod contract mirrors at load time.

import scenarioFixture from '../../../contract/fixtures/demo_scenario.json';
import runFixture from '../../../contract/fixtures/run.demo.json';
import { ApiError, type ApiClient } from './client';
import { parseRunResponse, parseScenarioResponse } from './parse';
import type {
  ApprovalDecisionRequest,
  ApprovalState,
  HealthResponse,
  RunResponse,
  ScenarioResponse,
} from './types';

const scenario = parseScenarioResponse(scenarioFixture);
const run = parseRunResponse(runFixture, scenario);

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export const fixtureClient: ApiClient = {
  async getHealth(): Promise<HealthResponse> {
    return { status: 'ok', offline: true, policy_engine: 'local-rule-engine@1.0.0' };
  },
  async getScenario(): Promise<ScenarioResponse> {
    return clone(scenario);
  },
  async createRun(): Promise<RunResponse> {
    // The fixture is a completed run; decideApproval returns a synthetic
    // decision (records-only, see FE-09 note in tasks.md).
    return clone(run);
  },
  startRun(): Promise<RunResponse> {
    return this.createRun('demo-v1');
  },
  async getRun(runId: string): Promise<RunResponse> {
    if (runId !== run.run_id) {
      throw new ApiError(404, 'RUN_NOT_FOUND', 'run not found');
    }
    return clone(run);
  },
  async decideApproval(_runId: string, req: ApprovalDecisionRequest): Promise<ApprovalState> {
    // Records a synthetic decision only — never applies anything.
    return {
      status: req.decision === 'approve' ? 'approved' : 'rejected',
      items: run.approval.items.map((item) => ({
        ...item,
        status: req.decision === 'approve' ? 'approved' : 'rejected',
        decided_by: req.decided_by ?? 'fixture-reviewer',
        decided_at: new Date().toISOString(),
        note: req.note ?? null,
        applied: false,
        simulated: true,
      })),
    };
  },
};
