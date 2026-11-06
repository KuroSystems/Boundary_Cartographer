// selectClient — the one switch between fixture and live data (FE-01).
// VITE_API_MODE=fixture (default) | live. Views only import apiClient/apiMode
// from here, so switching modes requires no view changes.

import type { ApiClient } from './client';
import { fixtureClient } from './fixtureClient';
import { httpClient } from './httpClient';

export type ApiMode = 'fixture' | 'live';

const raw = (import.meta.env.VITE_API_MODE as string | undefined) ?? 'fixture';

export const apiMode: ApiMode = raw === 'live' ? 'live' : 'fixture';

export const apiClient: ApiClient = apiMode === 'live' ? httpClient : fixtureClient;
