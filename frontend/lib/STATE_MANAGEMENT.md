# State Management Guide

This document describes the state management architecture for the AI Assistant frontend.

## Architecture Overview

The application uses a hybrid state management approach:

- **Zustand** for client-side UI state (immediate, local)
- **React Query** for server state (async, cached, synchronized)
- **WebSocket** for real-time updates and query invalidation

## Zustand Stores

Located in `/lib/stores/`, these handle fast, synchronous UI state.

### taskStore.ts

Manages task list UI state:
- `selectedTaskId` - Currently selected task
- `filter` - Task filter ('all' | 'enabled' | 'disabled')
- `sortBy` - Sort criteria ('name' | 'lastRun' | 'nextRun' | 'priority')
- `searchQuery` - Search filter text

**Usage:**
```tsx
import { useTaskStore } from '@/lib/stores';

function TaskList() {
  const { filter, setFilter, selectedTaskId, setSelectedTaskId } = useTaskStore();

  return (
    <div>
      <select value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="all">All Tasks</option>
        <option value="enabled">Enabled</option>
        <option value="disabled">Disabled</option>
      </select>
    </div>
  );
}
```

### uiStore.ts

Manages global UI state with persistence:
- `sidebarOpen` - Sidebar visibility
- `theme` - Theme preference ('light' | 'dark' | 'system')
- `terminalVisible` - Terminal panel visibility
- `notificationsOpen` - Notifications panel state

**Persistence:** Uses `zustand/middleware` to persist sidebar and theme preferences to localStorage.

**Usage:**
```tsx
import { useUiStore } from '@/lib/stores';

function Layout() {
  const { sidebarOpen, toggleSidebar, theme, setTheme } = useUiStore();

  return (
    <div className={theme}>
      <button onClick={toggleSidebar}>Toggle Sidebar</button>
      {sidebarOpen && <Sidebar />}
    </div>
  );
}
```

### terminalStore.ts

Manages terminal output buffer:
- `lines` - Array of terminal lines (max 1000)
- `currentExecutionId` - Active execution ID
- `isConnected` - WebSocket connection status
- `addLine()` - Add single line
- `addLines()` - Add multiple lines
- `clear()` - Clear buffer

**Usage:**
```tsx
import { useTerminalStore } from '@/lib/stores';

function Terminal() {
  const { lines, clear, isConnected } = useTerminalStore();

  return (
    <div>
      <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
      {lines.map(line => (
        <div key={line.id} className={line.type}>
          {line.content}
        </div>
      ))}
      <button onClick={clear}>Clear</button>
    </div>
  );
}
```

## React Query Hooks

Located in `/lib/hooks/`, these handle server state with automatic caching and invalidation.

### Query Configuration

The `QueryProvider` configures default behavior:
- **Stale time:** 30 seconds (data is fresh)
- **Cache time:** 5 minutes (inactive queries cached)
- **Retry:** 3 attempts with exponential backoff
- **Refetch on focus:** Production only

### Task Hooks (useTasks.ts)

**Queries:**
- `useTasks()` - Fetch all tasks
- `useTask(id)` - Fetch single task

**Mutations:**
- `useCreateTask()` - Create new task
- `useUpdateTask()` - Update existing task
- `useDeleteTask()` - Delete task
- `useToggleTask()` - Toggle enabled status

**Optimistic Updates:** All mutations use optimistic updates for instant UI feedback, with automatic rollback on error.

**Usage:**
```tsx
import { useTasks, useCreateTask, useUpdateTask } from '@/lib/hooks';

function TaskManager() {
  const { data: tasks, isLoading, error } = useTasks();
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();

  const handleCreate = async () => {
    await createTask.mutateAsync({
      name: 'New Task',
      command: 'echo',
      args: 'hello',
      schedule: '0 0 * * *',
    });
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    await updateTask.mutateAsync({
      id,
      data: { enabled: !enabled },
    });
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {tasks?.map(task => (
        <div key={task.id}>
          {task.name}
          <button onClick={() => handleToggle(task.id, task.enabled)}>
            {task.enabled ? 'Disable' : 'Enable'}
          </button>
        </div>
      ))}
      <button onClick={handleCreate}>Create Task</button>
    </div>
  );
}
```

### Execution Hooks (useTaskExecutions.ts)

**Queries:**
- `useTaskExecutions(taskId)` - Fetch executions for task
- `useExecution(id)` - Fetch single execution

**Utilities:**
- `useInvalidateExecutions()` - Manual invalidation (used by WebSocket)

**Usage:**
```tsx
import { useTaskExecutions } from '@/lib/hooks';

function ExecutionHistory({ taskId }: { taskId: string }) {
  const { data: executions, isLoading } = useTaskExecutions(taskId);

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h3>Execution History</h3>
      {executions?.map(exec => (
        <div key={exec.id}>
          {exec.status} - {exec.duration}ms
        </div>
      ))}
    </div>
  );
}
```

### Activity Log Hooks (useActivityLogs.ts)

**Queries:**
- `useActivityLogs(filters)` - Fetch activity logs with filters
- `useExecutionLogs(executionId)` - Fetch logs for execution

**Usage:**
```tsx
import { useActivityLogs, useExecutionLogs } from '@/lib/hooks';

function ActivityFeed() {
  const { data: logs } = useActivityLogs({ limit: 50, type: 'info' });

  return (
    <div>
      {logs?.map(log => (
        <div key={log.id}>
          [{log.type}] {log.message}
        </div>
      ))}
    </div>
  );
}

function ExecutionLogs({ executionId }: { executionId: string }) {
  const { data: logs } = useExecutionLogs(executionId);

  return (
    <div>
      {logs?.map(log => (
        <div key={log.id}>{log.message}</div>
      ))}
    </div>
  );
}
```

## WebSocket Integration

### useWebSocket Hook

The existing WebSocket hook provides:
- Automatic connection/reconnection
- Session-based authentication
- Message subscription
- Connection state management

### useWebSocketQuerySync Hook

New hook that bridges WebSocket and React Query:
- Listens to WebSocket messages
- Automatically invalidates relevant queries
- Updates terminal store
- Handles real-time updates

**Usage:**
```tsx
import { useWebSocketQuerySync } from '@/lib/hooks';

function App() {
  // Enable WebSocket → React Query synchronization
  const { isConnected } = useWebSocketQuerySync();

  return (
    <div>
      <StatusIndicator connected={isConnected} />
      {/* Rest of app */}
    </div>
  );
}
```

**Event Handling:**
- `terminal_output` → Updates terminal store
- `execution_start` → Invalidates tasks and executions
- `execution_complete` → Invalidates tasks, executions, and logs
- `status_update` → Invalidates specific execution
- `task_*` → Invalidates task queries
- `error` → Adds to terminal

## Query Keys

Hierarchical query keys for fine-grained cache control:

```typescript
// Tasks
['tasks']                          // All task queries
['tasks', 'list']                  // All task lists
['tasks', 'list', filters]         // Filtered list
['tasks', 'detail']                // All task details
['tasks', 'detail', id]            // Specific task

// Executions
['executions']                     // All execution queries
['executions', 'list']             // All execution lists
['executions', 'list', taskId]     // Task's executions
['executions', 'detail', id]       // Specific execution

// Activity Logs
['activityLogs']                   // All log queries
['activityLogs', 'list']           // All log lists
['activityLogs', 'list', filters]  // Filtered logs
['activityLogs', 'execution', id]  // Execution's logs
```

## Best Practices

### When to use Zustand

Use Zustand for:
- UI state (modals, panels, selections)
- Preferences (theme, layout)
- Ephemeral state (search queries, filters)
- State that doesn't need persistence to server

### When to use React Query

Use React Query for:
- Data from API endpoints
- Server-synchronized state
- Cached, shared data
- State that needs loading/error states

### Optimistic Updates

All mutations use optimistic updates:
1. Cancel in-flight queries
2. Snapshot current state
3. Immediately update cache
4. If mutation fails, rollback
5. Always refetch after settled

### Query Invalidation

Automatic invalidation happens via WebSocket:
- No manual refetching needed
- Real-time UI updates
- Efficient: only affected queries refetch

### Performance Tips

1. **Use selective invalidation:**
   ```tsx
   // Good: Invalidate specific query
   queryClient.invalidateQueries({ queryKey: ['tasks', 'detail', id] });

   // Bad: Invalidate everything
   queryClient.invalidateQueries({ queryKey: ['tasks'] });
   ```

2. **Enable queries conditionally:**
   ```tsx
   // Don't fetch if ID is null
   const { data } = useTask(taskId, { enabled: !!taskId });
   ```

3. **Use query prefetching:**
   ```tsx
   const queryClient = useQueryClient();

   // Prefetch on hover
   const handleHover = (id: string) => {
     queryClient.prefetchQuery({
       queryKey: ['tasks', 'detail', id],
       queryFn: () => fetchTask(id),
     });
   };
   ```

4. **Debounce search queries:**
   ```tsx
   const [search, setSearch] = useState('');
   const debouncedSearch = useDebounce(search, 300);
   const { data } = useTasks({ search: debouncedSearch });
   ```

## Testing

### Testing Zustand Stores

```tsx
import { renderHook, act } from '@testing-library/react';
import { useTaskStore } from '@/lib/stores';

test('updates filter', () => {
  const { result } = renderHook(() => useTaskStore());

  act(() => {
    result.current.setFilter('enabled');
  });

  expect(result.current.filter).toBe('enabled');
});
```

### Testing React Query Hooks

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useTasks } from '@/lib/hooks';

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

  expect(result.current.data).toHaveLength(3);
});
```

## Migration Guide

When adding new features:

1. **Add types** to `/lib/types/api.ts`
2. **Create hooks** in `/lib/hooks/`
3. **Export from index** in `/lib/hooks/index.ts`
4. **Add WebSocket events** to `useWebSocketQuerySync.ts`
5. **Update documentation** in this file

## Troubleshooting

### Stale data showing

- Check query keys are correct
- Verify WebSocket invalidation events
- Check staleTime and cacheTime settings

### Optimistic update not rolling back

- Ensure mutation returns error
- Check context is returned from onMutate
- Verify onError handler uses context

### WebSocket not updating queries

- Check WebSocket connection status
- Verify event types match
- Check query keys match between hook and WebSocket handler

### Performance issues

- Check for unnecessary re-renders
- Use React DevTools Profiler
- Verify query keys are stable (not recreated each render)
- Check if too many queries running simultaneously
