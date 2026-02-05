import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Task, CreateTaskInput, UpdateTaskInput } from '../types/api';

// Query keys
export const taskKeys = {
  all: ['tasks'] as const,
  lists: () => [...taskKeys.all, 'list'] as const,
  list: (filters?: Record<string, unknown>) => [...taskKeys.lists(), filters] as const,
  details: () => [...taskKeys.all, 'detail'] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
};

// Fetch all tasks
export function useTasks() {
  return useQuery({
    queryKey: taskKeys.lists(),
    queryFn: async (): Promise<Task[]> => {
      const response = await fetch('/api/tasks');
      if (!response.ok) {
        throw new Error('Failed to fetch tasks');
      }
      const data = await response.json();
      return data.tasks; // Extract tasks array from { tasks: [...] } response
    },
  });
}

// Fetch single task
export function useTask(id: string | null) {
  return useQuery({
    queryKey: taskKeys.detail(id ?? ''),
    queryFn: async (): Promise<Task> => {
      if (!id) throw new Error('Task ID is required');
      const response = await fetch(`/api/tasks/${id}`);
      if (!response.ok) {
        throw new Error('Failed to fetch task');
      }
      return response.json();
    },
    enabled: !!id,
  });
}

// Create task mutation
export function useCreateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateTaskInput): Promise<Task> => {
      const response = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create task');
      }
      return response.json();
    },
    onMutate: async (newTask) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() });

      // Snapshot previous value
      const previousTasks = queryClient.getQueryData<Task[]>(taskKeys.lists());

      // Optimistically update
      queryClient.setQueryData<Task[]>(taskKeys.lists(), (old = []) => [
        ...old,
        {
          id: 'temp-' + Date.now(),
          userId: '',
          ...newTask,
          enabled: newTask.enabled ?? true,
          priority: newTask.priority ?? 'default',
          notifyOn: newTask.notifyOn ?? 'completion,error',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          lastRun: null,
          nextRun: null,
          description: newTask.description ?? null,
          args: newTask.args ?? '',
        } as Task,
      ]);

      return { previousTasks };
    },
    onError: (err, newTask, context) => {
      // Rollback on error
      if (context?.previousTasks) {
        queryClient.setQueryData(taskKeys.lists(), context.previousTasks);
      }
    },
    onSettled: () => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Update task mutation
export function useUpdateTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateTaskInput }): Promise<Task> => {
      const response = await fetch(`/api/tasks/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to update task');
      }
      return response.json();
    },
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: taskKeys.detail(id) });
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() });

      const previousTask = queryClient.getQueryData<Task>(taskKeys.detail(id));
      const previousTasks = queryClient.getQueryData<Task[]>(taskKeys.lists());

      // Optimistically update single task
      if (previousTask) {
        queryClient.setQueryData<Task>(taskKeys.detail(id), {
          ...previousTask,
          ...data,
          updatedAt: new Date().toISOString(),
        });
      }

      // Optimistically update task list
      queryClient.setQueryData<Task[]>(taskKeys.lists(), (old = []) =>
        old.map((task) =>
          task.id === id
            ? { ...task, ...data, updatedAt: new Date().toISOString() }
            : task
        )
      );

      return { previousTask, previousTasks };
    },
    onError: (err, { id }, context) => {
      if (context?.previousTask) {
        queryClient.setQueryData(taskKeys.detail(id), context.previousTask);
      }
      if (context?.previousTasks) {
        queryClient.setQueryData(taskKeys.lists(), context.previousTasks);
      }
    },
    onSettled: (data, error, { id }) => {
      queryClient.invalidateQueries({ queryKey: taskKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Delete task mutation
export function useDeleteTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      const response = await fetch(`/api/tasks/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to delete task');
      }
    },
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: taskKeys.lists() });

      const previousTasks = queryClient.getQueryData<Task[]>(taskKeys.lists());

      // Optimistically remove from list
      queryClient.setQueryData<Task[]>(taskKeys.lists(), (old = []) =>
        old.filter((task) => task.id !== id)
      );

      return { previousTasks };
    },
    onError: (err, id, context) => {
      if (context?.previousTasks) {
        queryClient.setQueryData(taskKeys.lists(), context.previousTasks);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: taskKeys.lists() });
    },
  });
}

// Toggle task enabled status
export function useToggleTask() {
  const updateTask = useUpdateTask();

  return useMutation({
    mutationFn: async ({ id, enabled }: { id: string; enabled: boolean }) => {
      return updateTask.mutateAsync({ id, data: { enabled } });
    },
  });
}
