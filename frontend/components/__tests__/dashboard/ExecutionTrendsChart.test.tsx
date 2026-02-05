import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithQueryClient } from '../test-utils'
import { ExecutionTrendsChart } from '@/components/dashboard/ExecutionTrendsChart'

// Mock WebSocket hook
const mockSubscribe = vi.fn(() => vi.fn())
vi.mock('@/lib/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    isConnected: true,
    subscribe: mockSubscribe,
    send: vi.fn(),
  }),
}))

// Mock fetch globally for each test
const mockFetchResponses = new Map<string, any>()

beforeEach(() => {
  mockFetchResponses.clear()
  mockSubscribe.mockClear()

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

describe('ExecutionTrendsChart', () => {
  it('shows loading state initially', () => {
    renderWithQueryClient(<ExecutionTrendsChart />)

    expect(screen.getByText('Execution Trends (Last 7 Days)')).toBeInTheDocument()
    // Check for skeleton - it has a specific height class
    const skeleton = document.querySelector('.h-\\[300px\\]')
    expect(skeleton).toBeInTheDocument()
  })

  it('renders chart with trend data', async () => {
    const trendData = [
      { date: '2024-01-01', successful: 10, failed: 2, total: 12 },
      { date: '2024-01-02', successful: 8, failed: 1, total: 9 },
      { date: '2024-01-03', successful: 12, failed: 0, total: 12 },
    ]

    mockFetchResponses.set('/api/stats/execution-trends?days=7', trendData)

    renderWithQueryClient(<ExecutionTrendsChart />)

    await waitFor(() => {
      // Chart container should render (Recharts may not fully render SVG in test env)
      const chartContainer = document.querySelector('.recharts-responsive-container')
      expect(chartContainer).toBeInTheDocument()

      // Ensure empty state is NOT shown
      expect(screen.queryByText(/no execution data available/i)).not.toBeInTheDocument()
    })
  })

  it('shows empty state when no data', async () => {
    mockFetchResponses.set('/api/stats/execution-trends?days=7', [
      { date: '2024-01-01', successful: 0, failed: 0, total: 0 },
      { date: '2024-01-02', successful: 0, failed: 0, total: 0 },
    ])

    renderWithQueryClient(<ExecutionTrendsChart />)

    await waitFor(() => {
      expect(screen.getByText(/no execution data available/i)).toBeInTheDocument()
    })
  })

  it('displays error message on fetch failure', async () => {
    mockFetchResponses.set('/api/stats/execution-trends?days=7', {
      error: 'Failed to fetch trend data',
      status: 500,
    })

    renderWithQueryClient(<ExecutionTrendsChart />)

    await waitFor(() => {
      expect(screen.getByText(/failed to load trend data/i)).toBeInTheDocument()
    })
  })

  it('subscribes to WebSocket updates', () => {
    mockFetchResponses.set('/api/stats/execution-trends?days=7', [])

    renderWithQueryClient(<ExecutionTrendsChart />)

    // WebSocket subscription should be called with '*' channel
    expect(mockSubscribe).toHaveBeenCalledWith('*', expect.any(Function))
  })
})
