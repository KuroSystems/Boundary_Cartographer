// Demo data hooks (FE-01): every view reads through the ApiClient seam, so
// fixture/live switching needs no view changes.

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './selectClient';

export function useScenario() {
  return useQuery({ queryKey: ['scenario'], queryFn: () => apiClient.getScenario() });
}

export function useDemoRun() {
  return useQuery({
    queryKey: ['run', 'demo-v1'],
    queryFn: () => apiClient.createRun('demo-v1'),
  });
}
