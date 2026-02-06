import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MultiAgentBadge } from '../MultiAgentBadge'

describe('MultiAgentBadge', () => {
  it('renders agent count correctly', () => {
    render(<MultiAgentBadge agentCount={3} />)

    expect(screen.getByText(/3/)).toBeInTheDocument()
    expect(screen.getByText(/agent/i)).toBeInTheDocument()
  })

  it('shows synthesis indicator when enabled', () => {
    render(<MultiAgentBadge agentCount={3} hasSynthesis={true} />)

    // Check that synthesis is indicated (could be icon or text)
    const badge = screen.getByTestId('multi-agent-badge')
    expect(badge).toBeInTheDocument()

    // Check for synthesis icon or indicator
    const synthesisIcon = screen.getByTestId('synthesis-icon')
    expect(synthesisIcon).toBeInTheDocument()
  })

  it('hides synthesis indicator when disabled', () => {
    render(<MultiAgentBadge agentCount={3} hasSynthesis={false} />)

    // Synthesis icon should not be present
    const synthesisIcon = screen.queryByTestId('synthesis-icon')
    expect(synthesisIcon).not.toBeInTheDocument()
  })

  it('does not render with 0 agents', () => {
    const { container } = render(<MultiAgentBadge agentCount={0} />)

    // Component should return null and not render anything
    expect(container.firstChild).toBeNull()
  })

  it('applies custom className', () => {
    render(<MultiAgentBadge agentCount={3} className="custom-class" />)

    const badge = screen.getByTestId('multi-agent-badge')
    expect(badge).toHaveClass('custom-class')
  })

  it('renders correctly with 1 agent (singular)', () => {
    render(<MultiAgentBadge agentCount={1} />)

    // Should show "1 Agent" not "1 Agents"
    expect(screen.getByText(/1 agent$/i)).toBeInTheDocument()
  })

  it('renders correctly with multiple agents (plural)', () => {
    render(<MultiAgentBadge agentCount={5} />)

    expect(screen.getByText(/5 agents$/i)).toBeInTheDocument()
  })
})
