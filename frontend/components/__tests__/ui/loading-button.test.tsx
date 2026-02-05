import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { LoadingButton } from '@/components/ui/loading-button'

describe('LoadingButton', () => {
  it('renders children when not loading', () => {
    render(<LoadingButton>Save Task</LoadingButton>)

    expect(screen.getByText('Save Task')).toBeInTheDocument()
  })

  it('shows loading text when loading', () => {
    render(
      <LoadingButton loading={true} loadingText="Saving...">
        Save Task
      </LoadingButton>
    )

    expect(screen.getByText('Saving...')).toBeInTheDocument()
    expect(screen.queryByText('Save Task')).not.toBeInTheDocument()
  })

  it('is disabled when loading', () => {
    render(
      <LoadingButton loading={true}>
        Save Task
      </LoadingButton>
    )

    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
  })

  it('shows spinner when loading', () => {
    render(
      <LoadingButton loading={true}>
        Save Task
      </LoadingButton>
    )

    // Check for spinner SVG
    const svg = document.querySelector('svg.animate-spin')
    expect(svg).toBeInTheDocument()
  })

  it('calls onClick when not loading', async () => {
    const handleClick = vi.fn()

    render(
      <LoadingButton onClick={handleClick}>
        Save Task
      </LoadingButton>
    )

    const button = screen.getByRole('button')
    await userEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('does not call onClick when loading', async () => {
    const handleClick = vi.fn()

    render(
      <LoadingButton loading={true} onClick={handleClick}>
        Save Task
      </LoadingButton>
    )

    const button = screen.getByRole('button')
    // Button is disabled, so click won't trigger
    expect(button).toBeDisabled()
  })

  it('uses default loading text when not provided', () => {
    render(
      <LoadingButton loading={true}>
        Save Task
      </LoadingButton>
    )

    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('passes through button props', () => {
    render(
      <LoadingButton variant="destructive" size="sm">
        Delete
      </LoadingButton>
    )

    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-destructive')
  })
})
