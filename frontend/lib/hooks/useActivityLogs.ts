import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { ActivityLog } from '../types/api';

// Query keys
export const activityLogKeys = {
  all: ['activityLogs'] as const,
  lists: () => [...activityLogKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) => [...activityLogKeys.lists(), filters] as const,
  execution: (executionId: string) => [...activityLogKeys.all, 'execution', executionId] as const,
};

// Fetch all activity logs with optional filters
export function useActivityLogs(filters?: { limit?: number; type?: string }) {
  return useQuery({
    queryKey: activityLogKeys.list(filters),
    queryFn: async (): Promise<ActivityLog[]> => {
      const params = new URLSearchParams();
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.type) params.append('type', filters.type);

      const response = await fetch(`/api/activity-logs?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch activity logs');
      }
      return response.json();
    },
  });
}

// Fetch activity logs for a specific execution
export function useExecutionLogs(executionId: string | null) {
  return useQuery({
    queryKey: activityLogKeys.execution(executionId ?? ''),
    queryFn: async (): Promise<ActivityLog[]> => {
      if (!executionId) throw new Error('Execution ID is required');
      const response = await fetch(`/api/activity-logs?executionId=${executionId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch execution logs');
      }
      return response.json();
    },
    enabled: !!executionId,
  });
}

// Hook to invalidate activity log queries (called from WebSocket)
export function useInvalidateActivityLogs() {
  const queryClient = useQueryClient();

  return {
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: activityLogKeys.all });
    },
    invalidateExecution: (executionId: string) => {
      queryClient.invalidateQueries({ queryKey: activityLogKeys.execution(executionId) });
    },
  };
}
