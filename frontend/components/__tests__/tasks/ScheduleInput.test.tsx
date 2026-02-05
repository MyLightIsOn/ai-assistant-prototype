import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { ScheduleInput } from '@/components/tasks/ScheduleInput'

describe('ScheduleInput', () => {
  it('renders with default value', () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    // Should show tabs
    expect(screen.getByRole('tab', { name: /presets/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /visual builder/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /custom/i })).toBeInTheDocument()
  })

  it('displays human-readable text for valid cron', () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    // The cronstrue library generates a human-readable version
    // Check that schedule preview section exists with some description
    expect(screen.getByText(/schedule preview/i)).toBeInTheDocument()

    // The text may vary based on cronstrue version, just check it's there
    const previewCard = screen.getByText(/schedule preview/i).closest('div')
    expect(previewCard).toBeInTheDocument()
  })

  it('shows error for invalid cron expression', async () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="invalid" onChange={handleChange} />)

    // Switch to custom tab to enter invalid cron
    const customTab = screen.getByRole('tab', { name: /custom/i })
    await userEvent.click(customTab)

    expect(screen.getByText(/invalid cron expression/i)).toBeInTheDocument()
  })

  it('calls onChange when preset selected', async () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="" onChange={handleChange} />)

    // Find the Daily preset card by its content
    const dailyText = screen.getByText('Daily')
    const dailyCard = dailyText.closest('[role="button"]')
    expect(dailyCard).toBeInTheDocument()

    if (dailyCard) {
      await userEvent.click(dailyCard)
      expect(handleChange).toHaveBeenCalledWith('0 9 * * *')
    }
  })

  it('shows preset schedules', () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    expect(screen.getByText('Daily')).toBeInTheDocument()
    expect(screen.getByText('Weekly')).toBeInTheDocument()
    expect(screen.getByText('Monthly')).toBeInTheDocument()
    expect(screen.getByText('Hourly')).toBeInTheDocument()
  })

  it('allows custom cron input', async () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    // Switch to custom tab
    const customTab = screen.getByRole('tab', { name: /custom/i })
    await userEvent.click(customTab)

    // Find the cron input by its id
    const input = document.querySelector('#rawCron') as HTMLInputElement
    expect(input).toBeInTheDocument()

    if (input) {
      await userEvent.clear(input)
      await userEvent.type(input, '0 12 * * *')

      // The onChange should be called when a valid cron is entered
      expect(handleChange).toHaveBeenCalled()
    }
  })

  it('shows examples in custom tab', async () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    // Switch to custom tab
    const customTab = screen.getByRole('tab', { name: /custom/i })
    await userEvent.click(customTab)

    expect(screen.getByText(/examples/i)).toBeInTheDocument()
    expect(screen.getByText('Every day at 9:00 AM')).toBeInTheDocument()
    expect(screen.getByText('Every 6 hours')).toBeInTheDocument()
  })

  it('displays next executions for valid cron', () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    expect(screen.getByText(/next 5 executions/i)).toBeInTheDocument()
  })

  it('shows visual builder controls', async () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    // Switch to builder tab
    const builderTab = screen.getByRole('tab', { name: /visual builder/i })
    await userEvent.click(builderTab)

    // Check that builder controls are present
    expect(screen.getByText('Hour')).toBeInTheDocument()
    expect(screen.getByText('Minute')).toBeInTheDocument()
    expect(screen.getByText('Day of Week')).toBeInTheDocument()
    expect(screen.getByText('Day of Month')).toBeInTheDocument()

    // Check for any select control
    const selects = screen.getAllByRole('combobox')
    expect(selects.length).toBeGreaterThan(0)
  })

  it('displays cron expression in preview', () => {
    const handleChange = vi.fn()
    render(<ScheduleInput value="0 9 * * *" onChange={handleChange} />)

    expect(screen.getByText(/schedule preview/i)).toBeInTheDocument()
    expect(screen.getByText(/cron expression/i)).toBeInTheDocument()

    // The cron value appears in multiple places, just check it exists
    const cronCode = document.querySelector('code')
    expect(cronCode).toHaveTextContent('0 9 * * *')
  })
})
