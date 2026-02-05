import { renderHook, act } from '@testing-library/react';
import { useTerminalStore } from '../terminalStore';

describe('terminalStore', () => {
  beforeEach(() => {
    // Clear terminal before each test
    const { result } = renderHook(() => useTerminalStore());
    act(() => {
      result.current.clear();
    });
  });

  it('initializes with empty state', () => {
    const { result } = renderHook(() => useTerminalStore());

    expect(result.current.lines).toEqual([]);
    expect(result.current.currentExecutionId).toBeNull();
    expect(result.current.isConnected).toBe(false);
  });

  it('adds a line', () => {
    const { result } = renderHook(() => useTerminalStore());

    act(() => {
      result.current.addLine('Hello, world!');
    });

    expect(result.current.lines).toHaveLength(1);
    expect(result.current.lines[0].content).toBe('Hello, world!');
    expect(result.current.lines[0].type).toBe('stdout');
  });

  it('adds multiple lines', () => {
    const { result } = renderHook(() => useTerminalStore());

    const lines = [
      {
        id: '1',
        timestamp: new Date(),
        content: 'Line 1',
        type: 'stdout' as const,
      },
      {
        id: '2',
        timestamp: new Date(),
        content: 'Line 2',
        type: 'stderr' as const,
      },
    ];

    act(() => {
      result.current.addLines(lines);
    });

    expect(result.current.lines).toHaveLength(2);
    expect(result.current.lines[0].content).toBe('Line 1');
    expect(result.current.lines[1].content).toBe('Line 2');
  });

  it('limits lines to maxLines', () => {
    const { result } = renderHook(() => useTerminalStore());

    act(() => {
      // Add 1005 lines (maxLines is 1000)
      for (let i = 0; i < 1005; i++) {
        result.current.addLine(`Line ${i}`);
      }
    });

    expect(result.current.lines).toHaveLength(1000);
    expect(result.current.lines[0].content).toBe('Line 5');
    expect(result.current.lines[999].content).toBe('Line 1004');
  });

  it('clears terminal', () => {
    const { result } = renderHook(() => useTerminalStore());

    act(() => {
      result.current.addLine('Test line');
      result.current.setCurrentExecutionId('exec-123');
    });

    expect(result.current.lines).toHaveLength(1);

    act(() => {
      result.current.clear();
    });

    expect(result.current.lines).toEqual([]);
    expect(result.current.currentExecutionId).toBeNull();
  });

  it('sets current execution ID', () => {
    const { result } = renderHook(() => useTerminalStore());

    act(() => {
      result.current.setCurrentExecutionId('exec-456');
    });

    expect(result.current.currentExecutionId).toBe('exec-456');
  });

  it('sets connection status', () => {
    const { result } = renderHook(() => useTerminalStore());

    act(() => {
      result.current.setIsConnected(true);
    });

    expect(result.current.isConnected).toBe(true);
  });
});
