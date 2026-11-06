// Shared QueryClient factory (FE-01).

import { QueryClient } from '@tanstack/react-query';

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // The demo is offline/deterministic — no retries, moderate staleness.
        retry: false,
        staleTime: 30_000,
      },
    },
  });
}
