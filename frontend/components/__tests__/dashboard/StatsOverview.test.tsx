/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithQueryClient } from '../test-utils'
import { StatsOverview } from '@/components/dashboard/StatsOverview'

// Mock fetch globally for each test
const mockFetchResponses = new Map<string, any>()

beforeEach(() => {
  mockFetchResponses.clear()

  global.fetch = vi.fn((url: string | URL) => {
    const urlString = url.toString()
    const response = mockFetchResponses.get(urlString) || mockFetchResponses.get('default')

    if (response?.error) {
      return Promise.resolve({
        ok: false,
        status: response.status || 500,
        json: () => Promise.resolve({ error: response.error }),
      } as Response)
    }

    return Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response),
    } as Response)
  }) as any
})

describe('StatsOverview', () => {
  it('shows loading state initially', () => {
    renderWithQueryClient(<StatsOverview />)

    // Check for skeleton loading - the component renders 4 skeleton cards
    const cards = document.querySelectorAll('[data-slot="card"]')
    expect(cards.length).toBe(4)
  })

  it('displays stats when data loads', async () => {
    // Mock tasks API - note: useTasks expects { tasks: [...] } response
    mockFetchResponses.set('/api/tasks', {
      tasks: [
        { id: '1', name: 'Task 1', enabled: true },
        { id: '2', name: 'Task 2', enabled: true },
        { id: '3', name: 'Task 3', enabled: false },
      ]
    })

    // Mock success rate API
    mockFetchResponses.set('/api/stats/success-rate?days=7', {
      success_rate: 85.5,
      total_executions: 100,
      successful: 85,
      failed: 15,
    })

    renderWithQueryClient(<StatsOverview />)

    await waitFor(() => {
      expect(screen.getByText('Total Tasks')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument() // Total tasks
      expect(screen.getByText('2 active')).toBeInTheDocument() // Active tasks text
      expect(screen.getByText('85.5%')).toBeInTheDocument() // Success rate
    })
  })

  it('shows 0% success rate when no executions', async () => {
    mockFetchResponses.set('/api/tasks', { tasks: [] })
    mockFetchResponses.set('/api/stats/success-rate?days=7', {
      success_rate: 0,
      total_executions: 0,
      successful: 0,
      failed: 0,
    })

    renderWithQueryClient(<StatsOverview />)

    await waitFor(() => {
      expect(screen.getByText('0%')).toBeInTheDocument()
    })
  })

  it('displays error gracefully on fetch failure', async () => {
    // When fetch fails, the component still renders with default data
    mockFetchResponses.set('default', { error: 'Failed to load', status: 500 })

    renderWithQueryClient(<StatsOverview />)

    // Component should still render the structure even with failed fetches
    await waitFor(() => {
      const cards = document.querySelectorAll('[data-slot="card"]')
      expect(cards.length).toBeGreaterThan(0)
    }, { timeout: 3000 })
  })

  it('shows correct icons for each stat', async () => {
    mockFetchResponses.set('/api/tasks', { tasks: [{ id: '1', enabled: true }] })
    mockFetchResponses.set('/api/stats/success-rate?days=7', { success_rate: 100 })

    renderWithQueryClient(<StatsOverview />)

    await waitFor(() => {
      // Check for presence of stat icons (Calendar, CheckCircle2, etc.)
      const icons = document.querySelectorAll('svg')
      expect(icons.length).toBeGreaterThan(0)
    })
  })
})
