// useApproval (FE-09): records a decision through the adapter with an
// optimistic update that is rolled back on error. On a 409 conflict the
// state is refreshed from source (getRun). On success the run/graph data is
// deliberately NOT refetched — recording a decision never changes policy.

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ApiError } from '../api/client';
import type { ApiClient } from '../api/client';
import { apiClient } from '../api/selectClient';
import type { ApprovalDecisionRequest, ApprovalState, RunResponse } from '../api/types';

export function useApproval(run: RunResponse, client: ApiClient = apiClient) {
  const [state, setState] = useState<ApprovalState>(run.approval);
  const [conflict, setConflict] = useState(false);

  const mutation = useMutation({
    mutationFn: (req: ApprovalDecisionRequest) => client.decideApproval(run.run_id, req),
    onMutate: (req) => {
      // optimistic update; rolled back in onError
      setConflict(false);
      setState((prev) => ({
        status: req.decision === 'approve' ? 'approved' : 'rejected',
        items: prev.items.map((i) =>
          i.approval_id === req.approval_id
            ? {
                ...i,
                status: req.decision === 'approve' ? 'approved' : 'rejected',
                decided_by: req.decided_by ?? 'you',
                decided_at: new Date().toISOString(),
                note: req.note ?? i.note,
              }
            : i,
        ),
      }));
    },
    onError: (err) => {
      // roll back the optimistic update
      setState(run.approval);
      if (err instanceof ApiError && err.status === 409) {
        setConflict(true);
        // refresh from source: the item was already decided elsewhere
        void client.getRun(run.run_id).then((r) => setState(r.approval));
      }
    },
    onSuccess: (data) => {
      setState(data);
      setConflict(false);
    },
  });

  return {
    approval: state,
    conflict,
    deciding: mutation.isPending,
    error: mutation.error as Error | null,
    decide: (req: ApprovalDecisionRequest) => mutation.mutate(req),
  };
}
