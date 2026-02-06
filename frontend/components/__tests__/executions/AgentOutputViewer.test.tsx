import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentOutputViewer } from '@/components/executions/AgentOutputViewer'
import type { AgentOutput } from '@/components/executions/AgentOutputViewer'

describe('AgentOutputViewer', () => {
  it('renders tabs for each agent', () => {
    const agents: AgentOutput[] = [
      { agentName: 'Research Agent', status: 'completed' },
      { agentName: 'Execute Agent', status: 'running' },
      { agentName: 'Review Agent', status: 'pending' },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByRole('tab', { name: /research agent/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /execute agent/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /review agent/i })).toBeInTheDocument()
  })

  it('displays status badges in tabs', () => {
    const agents: AgentOutput[] = [
      { agentName: 'Research Agent', status: 'completed' },
      { agentName: 'Execute Agent', status: 'running' },
      { agentName: 'Review Agent', status: 'pending' },
      { agentName: 'Failed Agent', status: 'failed' },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText('Completed')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('displays structured output as formatted JSON', () => {
    const structuredData = {
      findings: ['Finding 1', 'Finding 2'],
      recommendations: ['Rec 1', 'Rec 2'],
    }

    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        structuredOutput: structuredData,
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    // Check for the section heading
    expect(screen.getByText('Structured Output (output.json):')).toBeInTheDocument()

    // Check that JSON is pretty-printed
    const jsonText = screen.getByText(/"findings":/i)
    expect(jsonText).toBeInTheDocument()
  })

  it('displays narrative output as text', () => {
    const narrativeContent = '# Research Findings\n\nFinding 1 details...'

    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        narrativeOutput: narrativeContent,
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText('Narrative Output (output.md):')).toBeInTheDocument()
    expect(screen.getByText(/research findings/i)).toBeInTheDocument()
  })

  it('shows empty state when agent has no outputs', () => {
    const agents: AgentOutput[] = [
      {
        agentName: 'Pending Agent',
        status: 'pending',
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText(/no outputs available yet/i)).toBeInTheDocument()
  })

  it('switches tabs when clicking different agents', async () => {
    const user = userEvent.setup()

    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        structuredOutput: { data: 'research' },
      },
      {
        agentName: 'Execute Agent',
        status: 'running',
        structuredOutput: { data: 'execute' },
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    // Initially, first tab should be active
    expect(screen.getByText(/"data": "research"/i)).toBeInTheDocument()

    // Click second tab
    const executeTab = screen.getByRole('tab', { name: /execute agent/i })
    await user.click(executeTab)

    // Second tab content should now be visible
    expect(screen.getByText(/"data": "execute"/i)).toBeInTheDocument()
  })

  it('displays only structured output when narrative is missing', () => {
    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        structuredOutput: { findings: ['test'] },
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText('Structured Output (output.json):')).toBeInTheDocument()
    expect(screen.queryByText('Narrative Output (output.md):')).not.toBeInTheDocument()
  })

  it('displays only narrative output when structured is missing', () => {
    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        narrativeOutput: '# Report\n\nDetails here',
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText('Narrative Output (output.md):')).toBeInTheDocument()
    expect(screen.queryByText('Structured Output (output.json):')).not.toBeInTheDocument()
  })

  it('displays both structured and narrative outputs', () => {
    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        structuredOutput: { findings: ['test'] },
        narrativeOutput: '# Report\n\nDetails here',
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText('Structured Output (output.json):')).toBeInTheDocument()
    expect(screen.getByText('Narrative Output (output.md):')).toBeInTheDocument()
  })

  it('applies custom className when provided', () => {
    const agents: AgentOutput[] = [
      { agentName: 'Test Agent', status: 'pending' },
    ]

    const { container } = render(
      <AgentOutputViewer agents={agents} className="custom-class" />
    )

    const element = container.firstChild as HTMLElement
    expect(element.className).toContain('custom-class')
  })

  it('handles empty agents array', () => {
    const agents: AgentOutput[] = []

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText(/no agents to display/i)).toBeInTheDocument()
  })

  it('uses correct badge variants for different statuses', () => {
    const agents: AgentOutput[] = [
      { agentName: 'Completed Agent', status: 'completed' },
      { agentName: 'Running Agent', status: 'running' },
      { agentName: 'Pending Agent', status: 'pending' },
      { agentName: 'Failed Agent', status: 'failed' },
    ]

    render(<AgentOutputViewer agents={agents} />)

    // Check that badges are rendered (will verify color classes in implementation)
    const completedBadge = screen.getByText('Completed')
    const runningBadge = screen.getByText('Running')
    const pendingBadge = screen.getByText('Pending')
    const failedBadge = screen.getByText('Failed')

    expect(completedBadge).toBeInTheDocument()
    expect(runningBadge).toBeInTheDocument()
    expect(pendingBadge).toBeInTheDocument()
    expect(failedBadge).toBeInTheDocument()
  })

  it('renders complex nested JSON structures correctly', () => {
    const complexData = {
      metadata: {
        timestamp: '2024-01-01',
        version: '1.0',
      },
      results: [
        { id: 1, value: 'test' },
        { id: 2, value: 'test2' },
      ],
    }

    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        structuredOutput: complexData,
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    expect(screen.getByText(/"metadata":/i)).toBeInTheDocument()
    expect(screen.getByText(/"results":/i)).toBeInTheDocument()
  })

  it('preserves markdown formatting in narrative output', () => {
    const markdown = '# Title\n\n## Subtitle\n\n- Item 1\n- Item 2\n\n**Bold text**'

    const agents: AgentOutput[] = [
      {
        agentName: 'Research Agent',
        status: 'completed',
        narrativeOutput: markdown,
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    // Check that the markdown content is present
    expect(screen.getByText(/title/i)).toBeInTheDocument()
    expect(screen.getByText(/subtitle/i)).toBeInTheDocument()
  })

  it('defaults to first tab when no tab is explicitly selected', () => {
    const agents: AgentOutput[] = [
      {
        agentName: 'First Agent',
        status: 'completed',
        structuredOutput: { first: true },
      },
      {
        agentName: 'Second Agent',
        status: 'completed',
        structuredOutput: { second: true },
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    // First tab content should be visible by default
    expect(screen.getByText(/"first": true/i)).toBeInTheDocument()
  })

  it('supports keyboard navigation between tabs', async () => {
    const user = userEvent.setup()

    const agents: AgentOutput[] = [
      {
        agentName: 'First Agent',
        status: 'completed',
        structuredOutput: { first: true },
      },
      {
        agentName: 'Second Agent',
        status: 'completed',
        structuredOutput: { second: true },
      },
    ]

    render(<AgentOutputViewer agents={agents} />)

    const firstTab = screen.getByRole('tab', { name: /first agent/i })

    // Focus the first tab
    firstTab.focus()
    expect(firstTab).toHaveFocus()

    // Should be able to navigate with arrow keys (Radix UI handles this)
    await user.keyboard('{ArrowRight}')

    const secondTab = screen.getByRole('tab', { name: /second agent/i })
    expect(secondTab).toHaveFocus()
  })
})
