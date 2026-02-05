import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { ConfirmDialog } from '@/components/error-handling/ConfirmDialog'

describe('ConfirmDialog', () => {
  it('does not render when closed', () => {
    render(
      <ConfirmDialog
        open={false}
        onOpenChange={vi.fn()}
        title="Delete Task"
        description="Are you sure?"
        onConfirm={vi.fn()}
      />
    )

    expect(screen.queryByText('Delete Task')).not.toBeInTheDocument()
  })

  it('renders when open', () => {
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={vi.fn()}
        title="Delete Task"
        description="Are you sure?"
        onConfirm={vi.fn()}
      />
    )

    expect(screen.getByText('Delete Task')).toBeInTheDocument()
    expect(screen.getByText('Are you sure?')).toBeInTheDocument()
  })

  it('calls onConfirm when confirm button clicked', async () => {
    const handleConfirm = vi.fn()

    render(
      <ConfirmDialog
        open={true}
        onOpenChange={vi.fn()}
        title="Delete Task"
        description="Are you sure?"
        confirmText="Delete"
        onConfirm={handleConfirm}
      />
    )

    const confirmButton = screen.getByRole('button', { name: /delete/i })
    await userEvent.click(confirmButton)

    expect(handleConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onOpenChange with false when cancel clicked', async () => {
    const handleOpenChange = vi.fn()

    render(
      <ConfirmDialog
        open={true}
        onOpenChange={handleOpenChange}
        title="Delete Task"
        description="Are you sure?"
        onConfirm={vi.fn()}
      />
    )

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    await userEvent.click(cancelButton)

    expect(handleOpenChange).toHaveBeenCalledWith(false)
  })

  it('renders with danger variant styling', () => {
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={vi.fn()}
        title="Delete Task"
        description="Are you sure?"
        confirmText="Delete"
        variant="danger"
        onConfirm={vi.fn()}
      />
    )

    const confirmButton = screen.getByRole('button', { name: /delete/i })
    expect(confirmButton).toHaveClass('bg-destructive')
    expect(confirmButton).toHaveClass('text-destructive-foreground')
  })

  it('uses default confirm text when not provided', () => {
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={vi.fn()}
        title="Delete Task"
        description="Are you sure?"
        onConfirm={vi.fn()}
      />
    )

    expect(screen.getByRole('button', { name: /confirm/i })).toBeInTheDocument()
  })
})
