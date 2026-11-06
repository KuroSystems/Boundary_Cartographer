// ErrorState — retryable error display with the contract error code (FE-03).

export function ErrorState({
  code,
  message,
  onRetry,
}: {
  code: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="panel" data-testid="error-state" role="alert">
      <h2>Run failed</h2>
      <p>
        Error code: <code className="mono">{code}</code>
      </p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
