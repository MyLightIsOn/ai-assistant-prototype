# Usage Examples

This document provides practical examples of using Zustand stores and React Query hooks in components.

## Example 1: Task List Component

```tsx
'use client';

import { useTasks, useDeleteTask } from '@/lib/hooks';
import { useTaskStore } from '@/lib/stores';

export function TaskList() {
  const { data: tasks, isLoading, error } = useTasks();
  const deleteTask = useDeleteTask();
  const { selectedTaskId, setSelectedTaskId, filter, searchQuery } = useTaskStore();

  // Filter tasks based on store state
  const filteredTasks = tasks?.filter(task => {
    // Apply filter
    if (filter === 'enabled' && !task.enabled) return false;
    if (filter === 'disabled' && task.enabled) return false;

    // Apply search
    if (searchQuery && !task.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    return true;
  });

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this task?')) {
      await deleteTask.mutateAsync(id);
      if (selectedTaskId === id) {
        setSelectedTaskId(null);
      }
    }
  };

  if (isLoading) {
    return <div className="p-4">Loading tasks...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-500">Error: {error.message}</div>;
  }

  return (
    <div className="space-y-2">
      {filteredTasks?.map(task => (
        <div
          key={task.id}
          className={`p-4 rounded border cursor-pointer ${
            selectedTaskId === task.id ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
          }`}
          onClick={() => setSelectedTaskId(task.id)}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{task.name}</h3>
              <p className="text-sm text-gray-600">{task.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-1 rounded text-xs ${
                  task.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                }`}
              >
                {task.enabled ? 'Enabled' : 'Disabled'}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(task.id);
                }}
                className="text-red-500 hover:text-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
```

## Example 2: Task Filter Controls

```tsx
'use client';

import { useTaskStore } from '@/lib/stores';

export function TaskFilters() {
  const { filter, setFilter, sortBy, setSortBy, searchQuery, setSearchQuery } = useTaskStore();

  return (
    <div className="flex gap-4 p-4 bg-gray-50 rounded">
      <input
        type="text"
        placeholder="Search tasks..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="flex-1 px-3 py-2 border rounded"
      />

      <select
        value={filter}
        onChange={(e) => setFilter(e.target.value as any)}
        className="px-3 py-2 border rounded"
      >
        <option value="all">All Tasks</option>
        <option value="enabled">Enabled Only</option>
        <option value="disabled">Disabled Only</option>
      </select>

      <select
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value as any)}
        className="px-3 py-2 border rounded"
      >
        <option value="name">Sort by Name</option>
        <option value="lastRun">Sort by Last Run</option>
        <option value="nextRun">Sort by Next Run</option>
        <option value="priority">Sort by Priority</option>
      </select>
    </div>
  );
}
```

## Example 3: Task Detail with Execution History

```tsx
'use client';

import { useTask, useTaskExecutions } from '@/lib/hooks';
import { useTaskStore } from '@/lib/stores';

export function TaskDetail() {
  const { selectedTaskId } = useTaskStore();
  const { data: task, isLoading: taskLoading } = useTask(selectedTaskId);
  const { data: executions, isLoading: executionsLoading } = useTaskExecutions(selectedTaskId);

  if (!selectedTaskId) {
    return <div className="p-4">Select a task to view details</div>;
  }

  if (taskLoading) {
    return <div className="p-4">Loading...</div>;
  }

  if (!task) {
    return <div className="p-4">Task not found</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <div>
        <h2 className="text-2xl font-bold">{task.name}</h2>
        <p className="text-gray-600">{task.description}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-semibold">Command</label>
          <p className="font-mono text-sm">{task.command} {task.args}</p>
        </div>
        <div>
          <label className="text-sm font-semibold">Schedule</label>
          <p className="font-mono text-sm">{task.schedule}</p>
        </div>
        <div>
          <label className="text-sm font-semibold">Last Run</label>
          <p className="text-sm">{task.lastRun ? new Date(task.lastRun).toLocaleString() : 'Never'}</p>
        </div>
        <div>
          <label className="text-sm font-semibold">Next Run</label>
          <p className="text-sm">{task.nextRun ? new Date(task.nextRun).toLocaleString() : 'N/A'}</p>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold mb-2">Execution History</h3>
        {executionsLoading ? (
          <div>Loading executions...</div>
        ) : executions && executions.length > 0 ? (
          <div className="space-y-2">
            {executions.map(exec => (
              <div key={exec.id} className="p-3 border rounded">
                <div className="flex justify-between items-center">
                  <span className={`font-semibold ${
                    exec.status === 'completed' ? 'text-green-600' :
                    exec.status === 'failed' ? 'text-red-600' :
                    'text-yellow-600'
                  }`}>
                    {exec.status}
                  </span>
                  <span className="text-sm text-gray-600">
                    {new Date(exec.startedAt).toLocaleString()}
                  </span>
                </div>
                {exec.duration && (
                  <p className="text-sm text-gray-500">Duration: {exec.duration}ms</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No executions yet</p>
        )}
      </div>
    </div>
  );
}
```

## Example 4: Create Task Form with Optimistic Updates

```tsx
'use client';

import { useState } from 'react';
import { useCreateTask } from '@/lib/hooks';
import { useTaskStore } from '@/lib/stores';

export function CreateTaskForm() {
  const createTask = useCreateTask();
  const { setSelectedTaskId } = useTaskStore();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    command: '',
    args: '',
    schedule: '0 0 * * *',
    enabled: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const newTask = await createTask.mutateAsync(formData);
      // Select the newly created task
      setSelectedTaskId(newTask.id);
      // Reset form
      setFormData({
        name: '',
        description: '',
        command: '',
        args: '',
        schedule: '0 0 * * *',
        enabled: true,
      });
    } catch (error) {
      console.error('Failed to create task:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4">
      <div>
        <label className="block text-sm font-semibold mb-1">Task Name</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
          className="w-full px-3 py-2 border rounded"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Description</label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          className="w-full px-3 py-2 border rounded"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Command</label>
        <input
          type="text"
          value={formData.command}
          onChange={(e) => setFormData({ ...formData, command: e.target.value })}
          required
          className="w-full px-3 py-2 border rounded font-mono"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Arguments</label>
        <input
          type="text"
          value={formData.args}
          onChange={(e) => setFormData({ ...formData, args: e.target.value })}
          className="w-full px-3 py-2 border rounded font-mono"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold mb-1">Schedule (Cron)</label>
        <input
          type="text"
          value={formData.schedule}
          onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
          required
          className="w-full px-3 py-2 border rounded font-mono"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="enabled"
          checked={formData.enabled}
          onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
        />
        <label htmlFor="enabled" className="text-sm">Enable task immediately</label>
      </div>

      <button
        type="submit"
        disabled={createTask.isPending}
        className="w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
      >
        {createTask.isPending ? 'Creating...' : 'Create Task'}
      </button>

      {createTask.isError && (
        <p className="text-red-500 text-sm">
          Error: {createTask.error.message}
        </p>
      )}
    </form>
  );
}
```

## Example 5: Terminal Component

```tsx
'use client';

import { useEffect, useRef } from 'react';
import { useTerminalStore } from '@/lib/stores';
import { useWebSocketQuerySync } from '@/lib/hooks';

export function Terminal() {
  const { lines, clear, isConnected } = useTerminalStore();
  const terminalRef = useRef<HTMLDivElement>(null);

  // Enable WebSocket sync
  useWebSocketQuerySync();

  // Auto-scroll to bottom when new lines added
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="flex flex-col h-full bg-black text-white font-mono text-sm">
      <div className="flex items-center justify-between p-2 bg-gray-800">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-xs">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <button
          onClick={clear}
          className="text-xs px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
        >
          Clear
        </button>
      </div>

      <div
        ref={terminalRef}
        className="flex-1 overflow-y-auto p-4 space-y-1"
      >
        {lines.map(line => (
          <div
            key={line.id}
            className={`${
              line.type === 'stderr' ? 'text-red-400' :
              line.type === 'system' ? 'text-blue-400' :
              'text-green-400'
            }`}
          >
            <span className="text-gray-500 mr-2">
              {line.timestamp.toLocaleTimeString()}
            </span>
            {line.content}
          </div>
        ))}
        {lines.length === 0 && (
          <div className="text-gray-500">Terminal output will appear here...</div>
        )}
      </div>
    </div>
  );
}
```

## Example 6: Theme Switcher with Persisted State

```tsx
'use client';

import { useUiStore } from '@/lib/stores';

export function ThemeSwitcher() {
  const { theme, setTheme } = useUiStore();

  return (
    <div className="flex gap-2">
      <button
        onClick={() => setTheme('light')}
        className={`px-3 py-1 rounded ${
          theme === 'light' ? 'bg-blue-500 text-white' : 'bg-gray-200'
        }`}
      >
        Light
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={`px-3 py-1 rounded ${
          theme === 'dark' ? 'bg-blue-500 text-white' : 'bg-gray-200'
        }`}
      >
        Dark
      </button>
      <button
        onClick={() => setTheme('system')}
        className={`px-3 py-1 rounded ${
          theme === 'system' ? 'bg-blue-500 text-white' : 'bg-gray-200'
        }`}
      >
        System
      </button>
    </div>
  );
}
```

## Example 7: Activity Feed with Real-time Updates

```tsx
'use client';

import { useActivityLogs } from '@/lib/hooks';
import { useWebSocketQuerySync } from '@/lib/hooks';

export function ActivityFeed() {
  const { data: logs, isLoading } = useActivityLogs({ limit: 50 });

  // Enable real-time updates
  useWebSocketQuerySync();

  if (isLoading) {
    return <div className="p-4">Loading activity...</div>;
  }

  return (
    <div className="space-y-2 p-4">
      <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
      {logs?.map(log => (
        <div
          key={log.id}
          className="flex items-start gap-3 p-3 bg-gray-50 rounded"
        >
          <div className={`w-2 h-2 rounded-full mt-2 ${
            log.type === 'error' ? 'bg-red-500' :
            log.type === 'warning' ? 'bg-yellow-500' :
            log.type === 'success' ? 'bg-green-500' :
            'bg-blue-500'
          }`} />
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-sm">{log.type}</span>
              <span className="text-xs text-gray-500">
                {new Date(log.createdAt).toLocaleString()}
              </span>
            </div>
            <p className="text-sm mt-1">{log.message}</p>
            {log.metadata && (
              <pre className="text-xs text-gray-600 mt-2 bg-gray-100 p-2 rounded">
                {log.metadata}
              </pre>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

## Example 8: Complete Page Layout

```tsx
'use client';

import { useUiStore } from '@/lib/stores';
import { TaskList } from './TaskList';
import { TaskDetail } from './TaskDetail';
import { TaskFilters } from './TaskFilters';
import { Terminal } from './Terminal';
import { CreateTaskForm } from './CreateTaskForm';

export function TasksPage() {
  const { sidebarOpen, terminalVisible, toggleSidebar, toggleTerminal } = useUiStore();

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-80 border-r bg-white flex flex-col">
          <div className="p-4 border-b">
            <h1 className="text-xl font-bold">Tasks</h1>
          </div>
          <TaskFilters />
          <div className="flex-1 overflow-y-auto">
            <TaskList />
          </div>
          <div className="p-4 border-t">
            <button className="w-full px-4 py-2 bg-blue-500 text-white rounded">
              Create Task
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between bg-white">
          <button onClick={toggleSidebar} className="px-3 py-1 bg-gray-100 rounded">
            {sidebarOpen ? 'Hide' : 'Show'} Sidebar
          </button>
          <button onClick={toggleTerminal} className="px-3 py-1 bg-gray-100 rounded">
            {terminalVisible ? 'Hide' : 'Show'} Terminal
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto">
          <TaskDetail />
        </div>

        {/* Terminal */}
        {terminalVisible && (
          <div className="h-64 border-t">
            <Terminal />
          </div>
        )}
      </div>
    </div>
  );
}
```
