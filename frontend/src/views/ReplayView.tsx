import { useDemoRun, useScenario } from '../api/useDemoData';
import { EventTimeline } from '../components/replay/EventTimeline';
import { UntrustedDocument } from '../components/replay/UntrustedDocument';
import { Skeleton } from '../components/Skeleton';
import { ErrorState } from '../components/ErrorState';

// ReplayView (FE-06): the /replay route — seeded untrusted document (escaped
// text only) + the replay event timeline.
export function ReplayView() {
  const run = useDemoRun();
  const scenario = useScenario();

  if (run.isLoading || scenario.isLoading) return <Skeleton label="Loading replay…" />;
  if (run.error || !run.data) {
    return (
      <ErrorState
        code="RUN_UNAVAILABLE"
        message={run.error instanceof Error ? run.error.message : 'unknown error'}
      />
    );
  }

  const doc = scenario.data?.document;

  return (
    <div>
      {doc && (
        <UntrustedDocument title={doc.title} content={doc.content} trustLevel={doc.trust_level} />
      )}
      <EventTimeline events={run.data.replay_events} />
    </div>
  );
}
