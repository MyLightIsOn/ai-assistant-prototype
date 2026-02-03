import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sidebar } from "../dashboard/Sidebar";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

describe("Sidebar", () => {
  it("renders the sidebar with navigation links", () => {
    render(<Sidebar />);

    // Check for the title
    expect(screen.getByText("AI Assistant")).toBeInTheDocument();

    // Check for all navigation items
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Tasks")).toBeInTheDocument();
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Terminal")).toBeInTheDocument();
    expect(screen.getByText("Activity")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();

    // Check for version
    expect(screen.getByText("AI Assistant v0.1.0")).toBeInTheDocument();
  });

  it("renders all navigation icons", () => {
    render(<Sidebar />);

    // Check that all icons are rendered (6 navigation items)
    const icons = document.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThanOrEqual(6);
  });

  it("highlights the active route", () => {
    render(<Sidebar />);

    // Find the Dashboard link (which should be active based on our mock)
    const dashboardLink = screen.getByText("Dashboard").closest("a");

    // Check that it has the active styling classes
    expect(dashboardLink?.className).toContain("bg-secondary");
  });
});
