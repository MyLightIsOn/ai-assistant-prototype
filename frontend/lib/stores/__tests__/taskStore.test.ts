import { renderHook, act } from '@testing-library/react';
import { useTaskStore } from '../taskStore';

describe('taskStore', () => {
  beforeEach(() => {
    // Reset store before each test
    const { result } = renderHook(() => useTaskStore());
    act(() => {
      result.current.setSelectedTaskId(null);
      result.current.setFilter('all');
      result.current.setSortBy('name');
      result.current.setSearchQuery('');
    });
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => useTaskStore());

    expect(result.current.selectedTaskId).toBeNull();
    expect(result.current.filter).toBe('all');
    expect(result.current.sortBy).toBe('name');
    expect(result.current.searchQuery).toBe('');
  });

  it('updates selected task ID', () => {
    const { result } = renderHook(() => useTaskStore());

    act(() => {
      result.current.setSelectedTaskId('task-123');
    });

    expect(result.current.selectedTaskId).toBe('task-123');
  });

  it('updates filter', () => {
    const { result } = renderHook(() => useTaskStore());

    act(() => {
      result.current.setFilter('enabled');
    });

    expect(result.current.filter).toBe('enabled');
  });

  it('updates sort by', () => {
    const { result } = renderHook(() => useTaskStore());

    act(() => {
      result.current.setSortBy('lastRun');
    });

    expect(result.current.sortBy).toBe('lastRun');
  });

  it('updates search query', () => {
    const { result } = renderHook(() => useTaskStore());

    act(() => {
      result.current.setSearchQuery('daily backup');
    });

    expect(result.current.searchQuery).toBe('daily backup');
  });
});
