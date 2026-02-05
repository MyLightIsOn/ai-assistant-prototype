import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';

interface UiStoreState {
  sidebarOpen: boolean;
  theme: Theme;
  terminalVisible: boolean;
  notificationsOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
  toggleTerminal: () => void;
  setTerminalVisible: (visible: boolean) => void;
  toggleNotifications: () => void;
  setNotificationsOpen: (open: boolean) => void;
}

export const useUiStore = create<UiStoreState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'dark',
      terminalVisible: false,
      notificationsOpen: false,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      toggleTerminal: () => set((state) => ({ terminalVisible: !state.terminalVisible })),
      setTerminalVisible: (visible) => set({ terminalVisible: visible }),
      toggleNotifications: () => set((state) => ({ notificationsOpen: !state.notificationsOpen })),
      setNotificationsOpen: (open) => set({ notificationsOpen: open }),
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarOpen: state.sidebarOpen,
        theme: state.theme,
      }),
    }
  )
);
