import { renderHook, act } from '@testing-library/react';
import { useUiStore } from '../uiStore';

describe('uiStore', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => useUiStore());

    expect(result.current.sidebarOpen).toBe(true);
    expect(result.current.theme).toBe('dark');
    expect(result.current.terminalVisible).toBe(false);
    expect(result.current.notificationsOpen).toBe(false);
  });

  it('toggles sidebar', () => {
    const { result } = renderHook(() => useUiStore());

    act(() => {
      result.current.toggleSidebar();
    });

    expect(result.current.sidebarOpen).toBe(false);

    act(() => {
      result.current.toggleSidebar();
    });

    expect(result.current.sidebarOpen).toBe(true);
  });

  it('sets theme', () => {
    const { result } = renderHook(() => useUiStore());

    act(() => {
      result.current.setTheme('light');
    });

    expect(result.current.theme).toBe('light');
  });

  it('toggles terminal', () => {
    const { result } = renderHook(() => useUiStore());

    act(() => {
      result.current.toggleTerminal();
    });

    expect(result.current.terminalVisible).toBe(true);
  });

  it('persists sidebar and theme to localStorage', () => {
    const { result } = renderHook(() => useUiStore());

    act(() => {
      result.current.setSidebarOpen(false);
      result.current.setTheme('light');
    });

    // Create new hook instance to test persistence
    const { result: result2 } = renderHook(() => useUiStore());

    expect(result2.current.sidebarOpen).toBe(false);
    expect(result2.current.theme).toBe('light');
  });
});
