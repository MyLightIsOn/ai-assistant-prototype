import { create } from 'zustand';

export type TaskFilter = 'all' | 'enabled' | 'disabled';
export type TaskSortBy = 'name' | 'lastRun' | 'nextRun' | 'priority';

interface TaskStoreState {
  selectedTaskId: string | null;
  filter: TaskFilter;
  sortBy: TaskSortBy;
  searchQuery: string;
  setSelectedTaskId: (id: string | null) => void;
  setFilter: (filter: TaskFilter) => void;
  setSortBy: (sortBy: TaskSortBy) => void;
  setSearchQuery: (query: string) => void;
}

export const useTaskStore = create<TaskStoreState>((set) => ({
  selectedTaskId: null,
  filter: 'all',
  sortBy: 'name',
  searchQuery: '',
  setSelectedTaskId: (id) => set({ selectedTaskId: id }),
  setFilter: (filter) => set({ filter }),
  setSortBy: (sortBy) => set({ sortBy }),
  setSearchQuery: (query) => set({ searchQuery: query }),
}));
