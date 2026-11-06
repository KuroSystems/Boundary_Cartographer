import { fixtureClient } from './fixtureClient';
import { httpClient } from './httpClient';
import { apiClient, apiMode } from './selectClient';
import type { ApiClient } from './client';

// Type-level conformance: both adapters satisfy the single ApiClient seam, so
// switching VITE_API_MODE requires no view changes.
const adapters: ApiClient[] = [fixtureClient, httpClient];

describe('ApiClient seam (FE-01)', () => {
  it('both fixture and http clients satisfy ApiClient', () => {
    for (const c of adapters) {
      expect(typeof c.getHealth).toBe('function');
      expect(typeof c.getScenario).toBe('function');
      expect(typeof c.createRun).toBe('function');
      expect(typeof c.getRun).toBe('function');
      expect(typeof c.decideApproval).toBe('function');
    }
  });

  it('defaults to fixture mode when VITE_API_MODE is unset', () => {
    expect(apiMode).toBe('fixture');
    expect(apiClient).toBe(fixtureClient);
  });

  it('fixture client serves the frozen demo scenario without a server', async () => {
    const scenario = await fixtureClient.getScenario();
    expect(scenario.scenario_id).toBe('demo-v1');
    expect(scenario.manifest.tools).toHaveLength(4);
    expect(scenario.identities).toHaveLength(2);
    expect(scenario.policy.rules.map((r) => r.id)).toEqual(['R1', 'R2', 'R3']);
  });

  it('fixture client serves the golden run with the expected verdicts', async () => {
    const run = await fixtureClient.createRun('demo-v1');
    const byId = Object.fromEntries(run.paths.map((p) => [p.path_id, p.status]));
    expect(byId).toEqual({
      P1: 'blocked',
      P2: 'blocked',
      P3: 'allowed',
      P4: 'disproved',
      P5: 'allowed',
    });
    expect(run.policy_diff.simulated).toBe(true);
    expect(run.retests.find((r) => r.retest_id === 'RT-2')?.actual).toBe('allowed');
  });

  it('fixture approval decision records only (applied=false, simulated=true)', async () => {
    const run = await fixtureClient.createRun('demo-v1');
    const state = await fixtureClient.decideApproval(run.run_id, {
      approval_id: 'ap-1',
      decision: 'approve',
      decided_by: 'test-reviewer',
    });
    expect(state.status).toBe('approved');
    expect(state.items[0].applied).toBe(false);
    expect(state.items[0].simulated).toBe(true);
  });
});
