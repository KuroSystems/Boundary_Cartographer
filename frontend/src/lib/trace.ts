// Reverse traceability lookups (FE-10): evidence -> paths/events, plus a
// resolution check that every evidence_id referenced by paths/reasons,
// retests, and replay events exists in the run's evidence list.

import type { EvidenceRecord, RunResponse } from '../api/types';

export interface TraceLinks {
  pathIds: string[];
  eventIds: string[];
}

/** evidence_id -> { pathIds, eventIds } built from the evidence records. */
export function buildTraceIndex(run: RunResponse): Map<string, TraceLinks> {
  const index = new Map<string, TraceLinks>();
  for (const rec of run.evidence) {
    const entry = index.get(rec.evidence_id) ?? { pathIds: [], eventIds: [] };
    entry.pathIds.push(...rec.trace.path_ids);
    entry.eventIds.push(...rec.trace.event_ids);
    index.set(rec.evidence_id, entry);
  }
  return index;
}

/** All evidence_ids referenced anywhere in the run. */
export function referencedEvidenceIds(run: RunResponse): string[] {
  const refs = new Set<string>();
  for (const p of run.paths) {
    for (const r of p.reasons) for (const e of r.evidence_ids) refs.add(e);
  }
  for (const e of run.replay_events) refs.add(e.event_id);
  return [...refs];
}

/** Referenced evidence_ids that do NOT resolve to a record in run.evidence. */
export function unresolvedEvidenceRefs(run: RunResponse): string[] {
  const known = new Set(run.evidence.map((e) => e.evidence_id));
  return referencedEvidenceIds(run).filter((id) => !known.has(id));
}

export function findEvidence(records: EvidenceRecord[], id: string): EvidenceRecord | undefined {
  return records.find((r) => r.evidence_id === id);
}

/** Hash-chain continuity: true when each record's prev_hash equals the previous hash. */
export function chainIsContinuous(records: EvidenceRecord[]): boolean {
  for (let i = 0; i < records.length; i++) {
    const prev = i === 0 ? null : records[i - 1].hash;
    if (records[i].prev_hash !== prev) return false;
  }
  return true;
}
