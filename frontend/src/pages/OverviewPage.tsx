import { useState } from 'react';
import { ScenarioOverview } from '../views/ScenarioOverview';
import { useDemoRun } from '../api/useDemoData';
import { PathTable } from '../components/PathTable';
import { ReasonList } from '../components/ReasonList';

// Overview route (FE-03/FE-05): scenario overview + run control, then the
// filterable path table and the selected path's reasons.
export function OverviewPage() {
  const run = useDemoRun();
  const [selected, setSelected] = useState<string | null>(null);

  const selectedPath = run.data?.paths.find((p) => p.path_id === selected) ?? null;

  return (
    <div>
      <ScenarioOverview />
      {run.data && (
        <>
          <PathTable
            paths={run.data.paths}
            counts={run.data.summary.counts}
            selected={selected}
            onSelect={setSelected}
          />
          <ReasonList path={selectedPath} />
        </>
      )}
    </div>
  );
}
