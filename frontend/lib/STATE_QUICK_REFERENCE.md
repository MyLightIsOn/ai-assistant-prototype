# State Management Quick Reference

## Import Paths

```tsx
// Stores
import { useTaskStore, useUiStore, useTerminalStore } from '@/lib/stores';

// Hooks
import { 
  useTasks, 
  useTask, 
  useCreateTask, 
  useUpdateTask, 
  useDeleteTask,
  useTaskExecutions,
  useActivityLogs,
  useWebSocketQuerySync 
} from '@/lib/hooks';

// Types
import type { Task, TaskExecution, ActivityLog } from '@/lib/types/api';
```

## Zustand Stores (Client State)

### Task Store
```tsx
const { 
  selectedTaskId,       // string | null
  filter,               // 'all' | 'enabled' | 'disabled'
  sortBy,               // 'name' | 'lastRun' | 'nextRun' | 'priority'
  searchQuery,          // string
  setSelectedTaskId,    // (id: string | null) => void
  setFilter,            // (filter: TaskFilter) => void
  setSortBy,            // (sortBy: TaskSortBy) => void
  setSearchQuery        // (query: string) => void
} = useTaskStore();
```

### UI Store (Persisted)
```tsx
const {
  sidebarOpen,          // boolean
  theme,                // 'light' | 'dark' | 'system'
  terminalVisible,      // boolean
  notificationsOpen,    // boolean
  toggleSidebar,        // () => void
  setSidebarOpen,       // (open: boolean) => void
  setTheme,             // (theme: Theme) => void
  toggleTerminal,       // () => void
  setTerminalVisible,   // (visible: boolean) => void
  toggleNotifications,  // () => void
  setNotificationsOpen  // (open: boolean) => void
} = useUiStore();
```

### Terminal Store
```tsx
const {
  lines,                // TerminalLine[]
  maxLines,             // number (1000)
  currentExecutionId,   // string | null
  isConnected,          // boolean
  addLine,              // (content: string, type?: 'stdout' | 'stderr' | 'system') => void
  addLines,             // (lines: TerminalLine[]) => void
  clear,                // () => void
  setCurrentExecutionId,// (id: string | null) => void
  setIsConnected        // (connected: boolean) => void
} = useTerminalStore();
```

## React Query Hooks (Server State)

### Task Queries
```tsx
// Fetch all tasks
const { data, isLoading, error } = useTasks();

// Fetch single task
const { data: task } = useTask(taskId);
```

### Task Mutations
```tsx
// Create task
const createTask = useCreateTask();
await createTask.mutateAsync({
  name: 'Task name',
  command: 'echo',
  args: 'hello',
  schedule: '0 0 * * *',
  enabled: true
});

// Update task
const updateTask = useUpdateTask();
await updateTask.mutateAsync({
  id: 'task-id',
  data: { enabled: false }
});

// Delete task
const deleteTask = useDeleteTask();
await deleteTask.mutateAsync('task-id');

// Toggle task
const toggleTask = useToggleTask();
await toggleTask.mutateAsync({ id: 'task-id', enabled: true });
```

### Execution Queries
```tsx
// Fetch task executions
const { data: executions } = useTaskExecutions(taskId);

// Fetch single execution
const { data: execution } = useExecution(executionId);
```

### Activity Log Queries
```tsx
// Fetch activity logs
const { data: logs } = useActivityLogs({ 
  limit: 50, 
  type: 'info' 
});

// Fetch execution logs
const { data: logs } = useExecutionLogs(executionId);
```

### WebSocket Sync
```tsx
// Enable WebSocket synchronization (call once at app level)
const { isConnected } = useWebSocketQuerySync();
```

## Common Patterns

### Task List with Filter
```tsx
function TaskList() {
  const { data: tasks } = useTasks();
  const { filter, selectedTaskId, setSelectedTaskId } = useTaskStore();

  const filtered = tasks?.filter(t => 
    filter === 'all' || 
    (filter === 'enabled' && t.enabled) ||
    (filter === 'disabled' && !t.enabled)
  );

  return (
    <div>
      {filtered?.map(task => (
        <div 
          key={task.id}
          onClick={() => setSelectedTaskId(task.id)}
          className={selectedTaskId === task.id ? 'selected' : ''}
        >
          {task.name}
        </div>
      ))}
    </div>
  );
}
```

### Create with Optimistic Update
```tsx
function CreateButton() {
  const createTask = useCreateTask();
  const { setSelectedTaskId } = useTaskStore();

  const handleCreate = async () => {
    const task = await createTask.mutateAsync({
      name: 'New Task',
      command: 'echo',
      args: 'test',
      schedule: '0 0 * * *'
    });
    setSelectedTaskId(task.id);
  };

  return (
    <button 
      onClick={handleCreate}
      disabled={createTask.isPending}
    >
      {createTask.isPending ? 'Creating...' : 'Create'}
    </button>
  );
}
```

### Loading States
```tsx
function TaskDetail({ taskId }: { taskId: string }) {
  const { data: task, isLoading, error } = useTask(taskId);

  if (isLoading) return <Spinner />;
  if (error) return <Error message={error.message} />;
  if (!task) return <NotFound />;

  return <div>{task.name}</div>;
}
```

### Real-time Terminal
```tsx
function Terminal() {
  const { lines, clear, isConnected } = useTerminalStore();
  useWebSocketQuerySync(); // Enable real-time updates

  return (
    <div>
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      {lines.map(line => (
        <div key={line.id}>{line.content}</div>
      ))}
      <button onClick={clear}>Clear</button>
    </div>
  );
}
```

## Query Keys (for manual invalidation)

```tsx
import { useQueryClient } from '@tanstack/react-query';
import { taskKeys, executionKeys, activityLogKeys } from '@/lib/hooks';

const queryClient = useQueryClient();

// Invalidate all tasks
queryClient.invalidateQueries({ queryKey: taskKeys.all });

// Invalidate task list
queryClient.invalidateQueries({ queryKey: taskKeys.lists() });

// Invalidate specific task
queryClient.invalidateQueries({ queryKey: taskKeys.detail(taskId) });

// Invalidate task executions
queryClient.invalidateQueries({ queryKey: executionKeys.list(taskId) });

// Invalidate activity logs
queryClient.invalidateQueries({ queryKey: activityLogKeys.all });
```

## TypeScript Types

```tsx
import type {
  Task,
  TaskExecution,
  ActivityLog,
  CreateTaskInput,
  UpdateTaskInput,
  WebSocketMessage,
} from '@/lib/types/api';

import type {
  TaskFilter,
  TaskSortBy,
  Theme,
  TerminalLine,
} from '@/lib/stores';
```

## Testing

```tsx
import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTaskStore } from '@/lib/stores';
import { useTasks } from '@/lib/hooks';

// Test store
test('updates filter', () => {
  const { result } = renderHook(() => useTaskStore());
  
  act(() => {
    result.current.setFilter('enabled');
  });
  
  expect(result.current.filter).toBe('enabled');
});

// Test query
test('fetches tasks', async () => {
  const queryClient = new QueryClient();
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  const { result } = renderHook(() => useTasks(), { wrapper });

  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true);
  });
});
```

## Troubleshooting

**Data not updating?**
- Check WebSocket connection: `useTerminalStore().isConnected`
- Verify `useWebSocketQuerySync()` is called
- Check browser console for WebSocket errors

**Optimistic update not working?**
- Ensure mutation returns data
- Check onMutate returns context
- Verify onError uses context for rollback

**Performance issues?**
- Use selective query invalidation
- Enable queries conditionally with `enabled` option
- Debounce search queries
- Check React DevTools Profiler
