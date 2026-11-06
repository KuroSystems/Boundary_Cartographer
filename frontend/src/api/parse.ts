// Parsing helpers (FE-02): validate untrusted JSON (fixtures, HTTP responses)
// against the Zod contract mirrors before any view touches it.

import { scenarioResponseSchema, runResponseSchemaFor, scenarioSourceIds } from './schemas';
import type { RunResponse, ScenarioResponse } from './types';

export class ParseError extends Error {
  constructor(
    public issues: string[],
  ) {
    super(`contract validation failed:\n${issues.join('\n')}`);
    this.name = 'ParseError';
  }
}

function formatIssues(error: { issues: { path: (string | number)[]; message: string }[] }): string[] {
  return error.issues.map((i) => `${i.path.join('.') || '(root)'}: ${i.message}`);
}

export function parseScenarioResponse(data: unknown): ScenarioResponse {
  const result = scenarioResponseSchema.safeParse(data);
  if (!result.success) throw new ParseError(formatIssues(result.error));
  return result.data as ScenarioResponse;
}

export function parseRunResponse(data: unknown, scenario?: ScenarioResponse): RunResponse {
  const schema = scenario
    ? runResponseSchemaFor(scenarioSourceIds(scenario))
    : runResponseSchemaFor();
  const result = schema.safeParse(data);
  if (!result.success) throw new ParseError(formatIssues(result.error));
  return result.data as RunResponse;
}
