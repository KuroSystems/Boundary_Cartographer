// EmptyState — no run yet; carries the Run CTA (FE-03).

import type { ReactNode } from 'react';

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel" data-testid="empty-state">
      <h2>{title}</h2>
      {message && <p>{message}</p>}
      {action}
    </div>
  );
}
