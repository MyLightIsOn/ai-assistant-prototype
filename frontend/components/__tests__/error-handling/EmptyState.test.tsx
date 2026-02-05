import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { EmptyState } from '@/components/error-handling/EmptyState'
import { Calendar } from 'lucide-react'

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(
      <EmptyState
        title="No tasks yet"
        description="Create your first task to get started"
      />
    )

    expect(screen.getByText('No tasks yet')).toBeInTheDocument()
    expect(screen.getByText('Create your first task to get started')).toBeInTheDocument()
  })

  it('renders custom icon', () => {
    render(
      <EmptyState
        icon={<Calendar data-testid="custom-icon" />}
        title="No tasks"
        description="Add a task"
      />
    )

    expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
  })

  it('renders action button when provided', () => {
    const handleClick = vi.fn()

    render(
      <EmptyState
        title="No tasks"
        description="Add a task"
        actionLabel="Create Task"
        onAction={handleClick}
      />
    )

    const button = screen.getByRole('button', { name: /create task/i })
    expect(button).toBeInTheDocument()
  })

  it('calls onAction when button clicked', async () => {
    const handleClick = vi.fn()

    render(
      <EmptyState
        title="No tasks"
        description="Add a task"
        actionLabel="Create Task"
        onAction={handleClick}
      />
    )

    const button = screen.getByRole('button', { name: /create task/i })
    await userEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('does not render button when no action provided', () => {
    render(
      <EmptyState
        title="No tasks"
        description="Add a task"
      />
    )

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
