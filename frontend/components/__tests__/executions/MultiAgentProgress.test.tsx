import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MultiAgentProgress } from '@/components/executions/MultiAgentProgress'
import type { Agent } from '@/components/executions/MultiAgentProgress'

describe('MultiAgentProgress', () => {
  it('renders with all pending agents', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'pending', role: 'research' },
      { name: 'Execute Agent', status: 'pending', role: 'execute' },
      { name: 'Review Agent', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Research Agent')).toBeInTheDocument()
    expect(screen.getByText('Execute Agent')).toBeInTheDocument()
    expect(screen.getByText('Review Agent')).toBeInTheDocument()
    expect(screen.getByText('Multi-Agent Execution Progress: 0%')).toBeInTheDocument()
  })

  it('renders with running agent', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'completed', role: 'research' },
      { name: 'Execute Agent', status: 'running', role: 'execute' },
      { name: 'Review Agent', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Research Agent')).toBeInTheDocument()
    expect(screen.getByText('Execute Agent')).toBeInTheDocument()
    expect(screen.getByText('Review Agent')).toBeInTheDocument()

    // Check for status text
    const completedElements = screen.getAllByText('Completed')
    expect(completedElements.length).toBeGreaterThan(0)

    const runningElements = screen.getAllByText('Running')
    expect(runningElements.length).toBeGreaterThan(0)

    const pendingElements = screen.getAllByText('Pending')
    expect(pendingElements.length).toBeGreaterThan(0)
  })

  it('renders with all completed agents', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'completed', role: 'research' },
      { name: 'Execute Agent', status: 'completed', role: 'execute' },
      { name: 'Review Agent', status: 'completed', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Multi-Agent Execution Progress: 100%')).toBeInTheDocument()

    // All agents should show as completed
    const completedElements = screen.getAllByText('Completed')
    expect(completedElements.length).toBe(3)
  })

  it('renders with failed agent', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'completed', role: 'research' },
      { name: 'Execute Agent', status: 'failed', role: 'execute' },
      { name: 'Review Agent', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    // Check for failed status
    const failedElements = screen.getAllByText('Failed')
    expect(failedElements.length).toBeGreaterThan(0)
  })

  it('calculates progress correctly at 33%', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'completed', role: 'research' },
      { name: 'Execute Agent', status: 'pending', role: 'execute' },
      { name: 'Review Agent', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Multi-Agent Execution Progress: 33%')).toBeInTheDocument()
  })

  it('calculates progress correctly at 66%', () => {
    const agents: Agent[] = [
      { name: 'Research Agent', status: 'completed', role: 'research' },
      { name: 'Execute Agent', status: 'completed', role: 'execute' },
      { name: 'Review Agent', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Multi-Agent Execution Progress: 67%')).toBeInTheDocument()
  })

  it('renders empty state when no agents provided', () => {
    const agents: Agent[] = []

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Multi-Agent Execution Progress: 0%')).toBeInTheDocument()
    expect(screen.getByText('No agents configured')).toBeInTheDocument()
  })

  it('applies custom className when provided', () => {
    const agents: Agent[] = [
      { name: 'Test Agent', status: 'pending', role: 'custom' },
    ]

    const { container } = render(
      <MultiAgentProgress agents={agents} className="custom-class" />
    )

    const element = container.firstChild as HTMLElement
    expect(element.className).toContain('custom-class')
  })

  it('shows correct status icons for each state', () => {
    const agents: Agent[] = [
      { name: 'Completed Agent', status: 'completed', role: 'research' },
      { name: 'Running Agent', status: 'running', role: 'execute' },
      { name: 'Failed Agent', status: 'failed', role: 'review' },
      { name: 'Pending Agent', status: 'pending', role: 'custom' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    // Check that all agent names are rendered
    expect(screen.getByText('Completed Agent')).toBeInTheDocument()
    expect(screen.getByText('Running Agent')).toBeInTheDocument()
    expect(screen.getByText('Failed Agent')).toBeInTheDocument()
    expect(screen.getByText('Pending Agent')).toBeInTheDocument()

    // Check for status badges with appropriate ARIA labels
    const completedBadge = screen.getByLabelText(/completed agent.*completed/i)
    expect(completedBadge).toBeInTheDocument()

    const runningBadge = screen.getByLabelText(/running agent.*running/i)
    expect(runningBadge).toBeInTheDocument()

    const failedBadge = screen.getByLabelText(/failed agent.*failed/i)
    expect(failedBadge).toBeInTheDocument()

    const pendingBadge = screen.getByLabelText(/pending agent.*pending/i)
    expect(pendingBadge).toBeInTheDocument()
  })

  it('supports custom role types', () => {
    const agents: Agent[] = [
      { name: 'Custom Agent', status: 'running', role: 'custom' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Custom Agent')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
  })

  it('handles single agent correctly', () => {
    const agents: Agent[] = [
      { name: 'Solo Agent', status: 'completed', role: 'research' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    expect(screen.getByText('Multi-Agent Execution Progress: 100%')).toBeInTheDocument()
    expect(screen.getByText('Solo Agent')).toBeInTheDocument()
  })

  it('counts running agents towards progress', () => {
    const agents: Agent[] = [
      { name: 'Agent 1', status: 'completed', role: 'research' },
      { name: 'Agent 2', status: 'running', role: 'execute' },
      { name: 'Agent 3', status: 'pending', role: 'review' },
    ]

    render(<MultiAgentProgress agents={agents} />)

    // Only completed agents count towards progress (1 out of 3 = 33%)
    expect(screen.getByText('Multi-Agent Execution Progress: 33%')).toBeInTheDocument()
  })
})
