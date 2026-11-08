import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';

export const useLaw = (docId: string | undefined) =>
  useQuery({ queryKey: ['law', docId], queryFn: () => api.law(docId!), enabled: !!docId });
