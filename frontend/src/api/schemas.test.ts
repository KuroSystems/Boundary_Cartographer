import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import runFixture from '../../../contract/fixtures/run.demo.json';
import scenarioFixture from '../../../contract/fixtures/demo_scenario.json';
import { parseRunResponse, parseScenarioResponse, ParseError } from './parse';
import { runResponseSchemaFor, scenarioResponseSchema, scenarioSourceIds } from './schemas';

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

describe('FE-02 contract fixtures parse', () => {
  it('demo_scenario.json parses against the Zod mirror', () => {
    const scenario = parseScenarioResponse(scenarioFixture);
    expect(scenario.scenario_id).toBe('demo-v1');
    expect(scenario.manifest.tools).toHaveLength(4);
  });

  it('run.demo.json parses against the Zod mirror (with scenario for invariant 5)', () => {
    const scenario = parseScenarioResponse(scenarioFixture);
    const run = parseRunResponse(runFixture, scenario);
    expect(run.paths).toHaveLength(5);
    expect(run.policy_diff.simulated).toBe(true);
  });
});

describe('FE-02 mutations fail with readable messages', () => {
  const parse = (mutate: (r: Record<string, unknown>) => void) => {
    const bad = clone(runFixture) as Record<string, unknown>;
    mutate(bad);
    return () => parseRunResponse(bad);
  };

  it('rejects an unknown top-level field (additionalProperties: false)', () => {
    expect(parse((r) => (r.surprise = 1))).toThrow(/surprise/);
  });

  it('rejects an invalid run status literal', () => {
    expect(parse((r) => (r.status = 'confirmed'))).toThrow(/status/);
  });

  it('rejects executed=true on a blocked event (invariant 3)', () => {
    expect(
      parse((r) => {
        const events = r.replay_events as Record<string, unknown>[];
        const blocked = events.find((e) => e.decision === 'blocked')!;
        blocked.executed = true;
      }),
    ).toThrow(/executed/);
  });

  it('rejects finance.export with executed=true (invariant 3)', () => {
    expect(
      parse((r) => {
        const events = r.replay_events as Record<string, unknown>[];
        const exp = events.find((e) => e.tool === 'finance.export')!;
        exp.decision = 'allowed';
        exp.executed = true;
      }),
    ).toThrow(/finance\.export/);
  });

  it('rejects RT-2 with actual != allowed (invariant 6)', () => {
    expect(
      parse((r) => {
        const retests = r.retests as Record<string, unknown>[];
        retests.find((t) => t.retest_id === 'RT-2')!.actual = 'blocked';
      }),
    ).toThrow(/RT-2/);
  });

  it('rejects policy_diff.simulated=false (invariant 7)', () => {
    expect(parse((r) => ((r.policy_diff as Record<string, unknown>).simulated = false))).toThrow(
      /simulated/,
    );
  });

  it('rejects approval item with applied=true (invariant 4)', () => {
    expect(
      parse((r) => {
        const items = (r.approval as Record<string, unknown>).items as Record<string, unknown>[];
        items[0].applied = true;
      }),
    ).toThrow(/applied/);
  });

  it('rejects an unresolvable evidence source_id when scenario is provided (invariant 5)', () => {
    const scenario = parseScenarioResponse(scenarioFixture);
    const bad = clone(runFixture) as Record<string, unknown>;
    ((bad.evidence as Record<string, unknown>[])[0].source_id = 'src:does-not-exist');
    expect(() => parseRunResponse(bad, scenario)).toThrow(/source_id/);
  });

  it('rejects a candidate path with reasons (invariant 1)', () => {
    expect(
      parse((r) => {
        const paths = r.paths as Record<string, unknown>[];
        const p = paths.find((x) => x.status === 'blocked')!;
        p.status = 'candidate';
      }),
    ).toThrow(/candidate/);
  });

  it('rejects a blocked path with empty reasons (invariant 2)', () => {
    expect(
      parse((r) => {
        const paths = r.paths as Record<string, unknown>[];
        paths.find((x) => x.status === 'blocked')!.reasons = [];
      }),
    ).toThrow(/reasons/);
  });

  it('ParseError message lists field-level issues', () => {
    const bad = clone(runFixture) as Record<string, unknown>;
    bad.status = 'confirmed';
    try {
      parseRunResponse(bad);
      expect.unreachable();
    } catch (e) {
      expect(e).toBeInstanceOf(ParseError);
      expect((e as ParseError).message).toMatch(/status/);
    }
  });
});

describe('FE-02 no hand-written status literals outside types.ts', () => {
  const SRC = join(__dirname, '..');
  const LITERALS = [
    'candidate',
    'allowed',
    'blocked',
    'disproved',
    'not_executed',
    'graph_reachability',
    'policy_verifier',
    'document_summarization',
    'finance_reporting',
  ];

  function* walk(dir: string): Generator<string> {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) yield* walk(full);
      else if (/\.tsx?$/.test(entry)) yield full;
    }
  }

  it('status literals appear only in types.ts (generated.ts is codegen)', () => {
    const offenders: string[] = [];
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file);
      if (rel.endsWith('types.ts') || rel.endsWith('generated.ts') || rel.endsWith('.test.ts') || rel.endsWith('.test.tsx')) {
        continue;
      }
      const text = readFileSync(file, 'utf-8');
      for (const lit of LITERALS) {
        if (text.includes(`'${lit}'`) || text.includes(`"${lit}"`)) {
          offenders.push(`${rel}: contains '${lit}'`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });

  it('schemas cover the invariant-bearing enums via types.ts const arrays', () => {
    const schema = runResponseSchemaFor(scenarioSourceIds(parseScenarioResponse(scenarioFixture)));
    expect(schema).toBeDefined();
    expect(scenarioResponseSchema).toBeDefined();
  });
});
