import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityLogItem } from "../ActivityLogItem";
import type { ActivityLog } from "@/lib/types/api";

const createMockLog = (overrides?: Partial<ActivityLog>): ActivityLog => ({
  id: "1",
  executionId: "exec-1",
  type: "task_start",
  message: "Test message",
  metadata: null,
  createdAt: new Date().toISOString(),
  ...overrides,
});

describe("ActivityLogItem", () => {
  it("renders task_start log correctly", () => {
    const log = createMockLog({
      type: "task_start",
      message: "Task 'Daily Backup' started",
    });

    render(<ActivityLogItem log={log} />);

    expect(screen.getByText("Task 'Daily Backup' started")).toBeInTheDocument();
  });

  it("renders task_complete log with success styling", () => {
    const log = createMockLog({
      type: "task_complete",
      message: "Task completed successfully",
      metadata: JSON.stringify({ duration: 1234, status: "success" }),
    });

    const { container } = render(<ActivityLogItem log={log} />);

    expect(screen.getByText("Task completed successfully")).toBeInTheDocument();
    // Check for success icon or styling
    const successIcon = container.querySelector('[data-icon="success"]');
    expect(successIcon || container.querySelector('.text-green-600')).toBeTruthy();
  });

  it("renders error log with error styling", () => {
    const log = createMockLog({
      type: "error",
      message: "Task failed: Connection timeout",
      metadata: JSON.stringify({ errorCode: "TIMEOUT" }),
    });

    const { container } = render(<ActivityLogItem log={log} />);

    expect(screen.getByText("Task failed: Connection timeout")).toBeInTheDocument();
    // Check for error icon or styling
    const errorIcon = container.querySelector('[data-icon="error"]');
    expect(errorIcon || container.querySelector('.text-red-600')).toBeTruthy();
  });

  it("renders notification_sent log correctly", () => {
    const log = createMockLog({
      type: "notification_sent",
      message: "Notification sent via ntfy",
      metadata: JSON.stringify({ priority: "high" }),
    });

    render(<ActivityLogItem log={log} />);

    expect(screen.getByText("Notification sent via ntfy")).toBeInTheDocument();
  });

  it("displays relative timestamp", () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const log = createMockLog({
      createdAt: fiveMinutesAgo,
    });

    render(<ActivityLogItem log={log} />);

    // Should display something like "5m ago"
    expect(screen.getByText(/\d+m ago/)).toBeInTheDocument();
  });

  it("displays metadata when available", () => {
    const log = createMockLog({
      type: "task_complete",
      message: "Task completed",
      metadata: JSON.stringify({ duration: 1234, exitCode: 0 }),
    });

    render(<ActivityLogItem log={log} />);

    // Duration should be displayed in seconds format (1.23s)
    expect(screen.getByText(/1\.23s/)).toBeInTheDocument();
  });

  it("handles logs without executionId", () => {
    const log = createMockLog({
      executionId: null,
      type: "system",
      message: "System notification",
    });

    render(<ActivityLogItem log={log} />);

    expect(screen.getByText("System notification")).toBeInTheDocument();
  });

  it("truncates long messages appropriately", () => {
    const longMessage = "a".repeat(200);
    const log = createMockLog({
      message: longMessage,
    });

    const { container } = render(<ActivityLogItem log={log} />);

    // Check that message container has truncation classes
    const messageElement = container.querySelector(".line-clamp-2, .truncate");
    expect(messageElement).toBeTruthy();
  });

  it("has correct icon for each log type", () => {
    const logTypes = [
      { type: "task_start", expectedIcon: "play" },
      { type: "task_complete", expectedIcon: "check" },
      { type: "error", expectedIcon: "error" },
      { type: "notification_sent", expectedIcon: "bell" },
    ];

    logTypes.forEach(({ type, expectedIcon }) => {
      const log = createMockLog({ type, message: `${type} message` });
      const { container } = render(<ActivityLogItem log={log} />);

      // Check for the expected icon
      const icon = container.querySelector(`[data-icon="${expectedIcon}"]`);
      expect(icon).toBeTruthy();
    });
  });

  it("is mobile responsive with compact layout", () => {
    const log = createMockLog();
    const { container } = render(<ActivityLogItem log={log} />);

    // Check for responsive classes
    const itemContainer = container.querySelector(
      ".flex, .grid, .flex-col, .sm\\:flex-row"
    );
    expect(itemContainer).toBeTruthy();
  });

  it("displays execution ID link when available", () => {
    const log = createMockLog({
      executionId: "exec-123",
      message: "Task started",
    });

    render(<ActivityLogItem log={log} />);

    // Should display execution ID in some form
    expect(screen.getByText(/exec-123/)).toBeInTheDocument();
  });
});
