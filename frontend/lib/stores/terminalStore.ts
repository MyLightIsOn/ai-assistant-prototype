import { create } from 'zustand';

export interface TerminalLine {
  id: string;
  timestamp: Date;
  content: string;
  type: 'stdout' | 'stderr' | 'system';
}

interface TerminalStoreState {
  lines: TerminalLine[];
  maxLines: number;
  currentExecutionId: string | null;
  isConnected: boolean;
  addLine: (content: string, type?: TerminalLine['type']) => void;
  addLines: (lines: TerminalLine[]) => void;
  clear: () => void;
  setCurrentExecutionId: (id: string | null) => void;
  setIsConnected: (connected: boolean) => void;
}

export const useTerminalStore = create<TerminalStoreState>((set) => ({
  lines: [],
  maxLines: 1000,
  currentExecutionId: null,
  isConnected: false,

  addLine: (content, type = 'stdout') =>
    set((state) => {
      const newLine: TerminalLine = {
        id: `${Date.now()}-${Math.random()}`,
        timestamp: new Date(),
        content,
        type,
      };

      const newLines = [...state.lines, newLine];

      // Keep only the last maxLines
      if (newLines.length > state.maxLines) {
        return { lines: newLines.slice(newLines.length - state.maxLines) };
      }

      return { lines: newLines };
    }),

  addLines: (newLines) =>
    set((state) => {
      const allLines = [...state.lines, ...newLines];

      if (allLines.length > state.maxLines) {
        return { lines: allLines.slice(allLines.length - state.maxLines) };
      }

      return { lines: allLines };
    }),

  clear: () => set({ lines: [], currentExecutionId: null }),

  setCurrentExecutionId: (id) => set({ currentExecutionId: id }),

  setIsConnected: (connected) => set({ isConnected: connected }),
}));
