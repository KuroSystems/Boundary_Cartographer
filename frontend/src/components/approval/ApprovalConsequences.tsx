// ApprovalConsequences (FE-09): the explicit, always-visible statement of what
// recording a decision does — and does not — do.
export function ApprovalConsequences() {
  return (
    <div className="panel consequences" data-testid="approval-consequences" role="note">
      <h2>What this decision does</h2>
      <p className="consequences-text">
        Recorded decision only. No policy was applied and no export was performed. The approval queue
        never executes anything: <code className="mono">applied</code> stays{' '}
        <code className="mono">false</code>, <code className="mono">simulated</code> stays{' '}
        <code className="mono">true</code>.
      </p>
    </div>
  );
}
