import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

/** Polls /api/health; retries quickly while the backend is down so the banner clears on its own. */
export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    retry: false,
    refetchInterval: (q) =>
      q.state.status === 'error' || q.state.data?.status === 'degraded' ? 5000 : 60000,
  });
