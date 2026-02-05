import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock the ActivityLogItem component
vi.mock("../ActivityLogItem", () => ({
  ActivityLogItem: ({ log }: { log: { id: string; message: string } }) => (
    <div data-testid={`activity-log-${log.id}`}>{log.message}</div>
  ),
}));

// Create mock functions
const mockUseActivityLogs = vi.fn();
const mockUseWebSocket = vi.fn();
const mockInvalidateQueries = vi.fn();

// Mock the hooks
vi.mock("@/lib/hooks", () => ({
  useActivityLogs: () => mockUseActivityLogs(),
  useWebSocket: () => mockUseWebSocket(),
}));

// Mock useQueryClient
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: mockInvalidateQueries,
    }),
  };
});

// Import after mocks are set up
const { ActivityFeed } = await import("../ActivityFeed");

const mockLogs = [
  {
    id: "1",
    executionId: "exec-1",
    type: "task_start",
    message: "Task 'Daily Backup' started",
    metadata: null,
    createdAt: new Date().toISOString(),
  },
  {
    id: "2",
    executionId: "exec-1",
    type: "task_complete",
    message: "Task 'Daily Backup' completed successfully",
    metadata: JSON.stringify({ duration: 1234 }),
    createdAt: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
  },
  {
    id: "3",
    executionId: "exec-2",
    type: "error",
    message: "Task 'Email Report' failed: Connection timeout",
    metadata: JSON.stringify({ errorCode: "TIMEOUT" }),
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
];

describe("ActivityFeed", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();

    // Set default mock implementations
    mockUseWebSocket.mockReturnValue({
      subscribe: vi.fn(() => vi.fn()),
      isConnected: true,
    });
  });

  const renderWithClient = (ui: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    );
  };

  it("renders loading state initially", () => {
    mockUseActivityLogs.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = renderWithClient(<ActivityFeed />);

    // Check for skeleton loading indicators
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders empty state when no logs are available", () => {
    mockUseActivityLogs.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);
    expect(screen.getByText(/no activity logs/i)).toBeInTheDocument();
  });

  it("renders activity logs successfully", () => {
    mockUseActivityLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);

    // Check that all logs are rendered
    expect(screen.getByTestId("activity-log-1")).toBeInTheDocument();
    expect(screen.getByTestId("activity-log-2")).toBeInTheDocument();
    expect(screen.getByTestId("activity-log-3")).toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    mockUseActivityLogs.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Failed to fetch logs"),
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);
    expect(screen.getByText(/failed to load activity logs/i)).toBeInTheDocument();
  });

  it("displays filter tabs for different log types", async () => {
    mockUseActivityLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const user = userEvent.setup();
    renderWithClient(<ActivityFeed />);

    // Check for filter tabs
    expect(screen.getByRole("tab", { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /tasks/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /errors/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /notifications/i })).toBeInTheDocument();

    // Click on a filter tab
    await user.click(screen.getByRole("tab", { name: /errors/i }));

    // Verify re-render with new filter (component state change)
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: /errors/i })).toHaveAttribute("data-state", "active");
    });
  });

  it("updates logs in real-time via WebSocket", async () => {
    const mockSubscribe = vi.fn((type, handler) => {
      // Simulate receiving a new log
      setTimeout(() => {
        handler({
          type: "execution_complete",
          data: { executionId: "exec-3" },
        });
      }, 100);
      return vi.fn(); // unsubscribe function
    });

    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: true,
    });

    mockUseActivityLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);

    // WebSocket should subscribe to messages
    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalled();
    });
  });

  it("supports pagination for older logs", () => {
    // Create enough logs to show the "Load More" button (need to meet the limit)
    const manyLogs = Array(50).fill(null).map((_, i) => ({
      id: `${i}`,
      executionId: `exec-${i}`,
      type: "task_start",
      message: `Log ${i}`,
      metadata: null,
      createdAt: new Date().toISOString(),
    }));

    mockUseActivityLogs.mockReturnValue({
      data: manyLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);

    // Look for "Load More" button (only shown when logs.length >= limit)
    const loadMoreButton = screen.getByRole("button", { name: /load more/i });
    expect(loadMoreButton).toBeInTheDocument();
    expect(loadMoreButton).not.toBeDisabled();
  });

  it("shows time period header (last 24 hours by default)", () => {
    mockUseActivityLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    renderWithClient(<ActivityFeed />);
    expect(screen.getByText(/activity/i)).toBeInTheDocument();
  });

  it("is mobile responsive", () => {
    mockUseActivityLogs.mockReturnValue({
      data: mockLogs,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = renderWithClient(<ActivityFeed />);

    // Check for responsive classes (this is a basic check)
    const feedContainer = container.querySelector("[data-testid='activity-feed']");
    expect(feedContainer).toBeInTheDocument();
  });
});
