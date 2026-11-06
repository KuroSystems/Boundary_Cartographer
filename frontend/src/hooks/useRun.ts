// useRun — run-control state machine (FE-03): idle → pending → success/error.
// Wraps a useMutation over ApiClient.startRun; views never call fetch directly.

import { useMutation } from '@tanstack/react-query';
import type { ApiClient } from '../api/client';
import { apiClient } from '../api/selectClient';
import type { RunResponse } from '../api/types';

export type RunStatus = 'idle' | 'pending' | 'success' | 'error';

export function useRun(client: ApiClient = apiClient) {
  const mutation = useMutation({
    mutationFn: () => client.startRun('demo-v1'),
  });
  return {
    run: (mutation.data ?? null) as RunResponse | null,
    status: mutation.status as RunStatus,
    error: mutation.error as Error | null,
    startRun: () => mutation.mutate(),
    reset: () => mutation.reset(),
  };
}
