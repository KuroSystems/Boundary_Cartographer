import { useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useDemoRun } from '../api/useDemoData';
import { EvidenceDrawer } from '../components/evidence/EvidenceDrawer';
import { EvidenceTable } from '../components/evidence/EvidenceTable';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';
import { findEvidence } from '../lib/trace';

// EvidenceView (FE-10): the /evidence route — filterable evidence table plus a
// drawer opened via the #<evidence_id> URL hash (linked from path reasons and
// replay source ids).
export function EvidenceView() {
  const run = useDemoRun();
  const location = useLocation();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const hashId = useMemo(() => {
    const h = location.hash.replace(/^#/, '');
    return h ? decodeURIComponent(h) : null;
  }, [location.hash]);

  if (run.isLoading) return <Skeleton label="Loading evidence…" />;
  if (run.error || !run.data) {
    return (
      <ErrorState
        code="RUN_UNAVAILABLE"
        message={run.error instanceof Error ? run.error.message : 'unknown error'}
      />
    );
  }

  const records = run.data.evidence;
  const activeId = hashId ?? selectedId;
  const drawerRecord = activeId ? findEvidence(records, activeId) ?? null : null;

  return (
    <div className="evidence-view">
      <EvidenceTable
        records={records}
        selectedId={activeId}
        onSelect={(id) => setSelectedId(id)}
      />
      <EvidenceDrawer record={drawerRecord} onClose={() => setSelectedId(null)} />
    </div>
  );
}
