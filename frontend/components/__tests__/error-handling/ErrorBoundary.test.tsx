import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorBoundary } from '@/components/error-handling/ErrorBoundary'

const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error')
  }
  return <div>No error</div>
}

describe('ErrorBoundary', () => {
  // Suppress console.error for cleaner test output
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    )

    expect(screen.getByText('No error')).toBeInTheDocument()
  })

  it('renders error fallback when error occurs', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('shows error message in fallback', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText(/test error/i)).toBeInTheDocument()
  })

  it('resets error state when try again clicked', async () => {
    // Use a ref to track if we should throw
    let shouldThrow = true
    const ConditionalThrow = () => {
      if (shouldThrow) {
        throw new Error('Test error')
      }
      return <div>No error</div>
    }

    const { unmount } = render(
      <ErrorBoundary>
        <ConditionalThrow />
      </ErrorBoundary>
    )

    // Verify error is showing
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument()

    const tryAgainButton = screen.getByRole('button', { name: /try again/i })

    // Change the condition before clicking reset
    shouldThrow = false

    // Click Try Again - this should clear error state and re-render children
    await userEvent.click(tryAgainButton)

    // The component should now render without error
    expect(screen.getByText('No error')).toBeInTheDocument()

    unmount()
  })
})
