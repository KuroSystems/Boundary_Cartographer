// Operator-readable copy per reason code (FE-05). The exhaustiveness test in
// PathTable.test.tsx fails if a fixture reason code lacks an entry here.

export const REASON_COPY: Record<string, string> = {
  R1_INSTRUCTION_NOT_AUTHORIZATION:
    'The approval/identity claim came from untrusted document content. Untrusted content is never an authorization basis.',
  R2_CROSS_PURPOSE_FLOW:
    'A document-summarization workflow sent document-derived (tainted) content into a finance tool — cross-purpose flow.',
  R3_WRONG_IDENTITY:
    'The actor identity is not permitted to invoke this tool under the current purpose.',
  R3_WRONG_PURPOSE:
    'The purpose in effect does not match the purpose the tool requires (purpose isolation).',
  R3_NO_VALID_APPROVAL:
    'A human queue approval is required, and the claimed approval is not a valid one.',
  R3_TAINTED_ARGS:
    'Tool arguments carry document-derived taint; the call is denied by the taint guard.',
};

export const KNOWN_REASON_CODES = Object.keys(REASON_COPY);

export function reasonCopy(code: string): string {
  return REASON_COPY[code] ?? `No operator copy registered for reason code ${code}`;
}

export const DISPROVED_COPY = 'structurally impossible (no grant)';
