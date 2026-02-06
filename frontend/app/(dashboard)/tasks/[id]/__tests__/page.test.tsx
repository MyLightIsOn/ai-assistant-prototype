/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import TaskDetailPage from '../page'

// Mock Next.js navigation
vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-task-id' }),
  useRouter: () => ({
    push: vi.fn(),
    back: vi.fn(),
  }),
}))

// Mock hooks
const mockUseTask = vi.fn()
const mockUseTaskExecutions = vi.fn()
const mockUseWebSocket = vi.fn()

vi.mock('@/lib/hooks/useTasks', () => ({
  useTask: () => mockUseTask(),
}))

vi.mock('@/lib/hooks/useTaskExecutions', () => ({
  useTaskExecutions: () => mockUseTaskExecutions(),
}))

vi.mock('@/lib/hooks/useWebSocket', () => ({
  useWebSocket: () => mockUseWebSocket(),
}))

// Mock components
vi.mock('@/components/executions/MultiAgentProgress', () => ({
  MultiAgentProgress: ({ agents }: any) => (
    <div data-testid="multi-agent-progress">
      {agents.map((agent: any) => (
        <div key={agent.name}>{agent.name}: {agent.status}</div>
      ))}
    </div>
  ),
}))

vi.mock('@/components/executions/AgentOutputViewer', () => ({
  AgentOutputViewer: ({ agents }: any) => (
    <div data-testid="agent-output-viewer">
      {agents.map((agent: any) => (
        <div key={agent.agentName}>{agent.agentName}</div>
      ))}
    </div>
  ),
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    {children}
  </QueryClientProvider>
)

describe('TaskDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Default mock implementations
    mockUseWebSocket.mockReturnValue({
      subscribe: vi.fn(() => vi.fn()),
      isConnected: true,
    })
  })

  describe('Standard Task (non-multi-agent)', () => {
    beforeEach(() => {
      mockUseTask.mockReturnValue({
        data: {
          id: 'test-task-id',
          name: 'Test Task',
          description: 'Test description',
          command: 'test-command',
          args: '',
          schedule: '0 0 * * *',
          enabled: true,
          priority: 'default',
          notifyOn: 'completion,error',
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
          lastRun: null,
          nextRun: null,
        },
        isLoading: false,
        refetch: vi.fn(),
      })

      mockUseTaskExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      })
    })

    it('renders task details without multi-agent UI', () => {
      render(<TaskDetailPage />, { wrapper })

      expect(screen.getByText('Test Task')).toBeInTheDocument()
      expect(screen.getByText('Test description')).toBeInTheDocument()
      expect(screen.queryByTestId('multi-agent-progress')).not.toBeInTheDocument()
      expect(screen.queryByTestId('agent-output-viewer')).not.toBeInTheDocument()
    })

    it('shows execution history section', () => {
      render(<TaskDetailPage />, { wrapper })

      expect(screen.getByText('Execution History')).toBeInTheDocument()
      expect(screen.getByText('Recent task executions and their status')).toBeInTheDocument()
    })
  })

  describe('Multi-Agent Task', () => {
    beforeEach(() => {
      mockUseTask.mockReturnValue({
        data: {
          id: 'test-task-id',
          name: 'Multi-Agent Task',
          description: 'Multi-agent test',
          command: 'test-command',
          args: '',
          schedule: '0 0 * * *',
          enabled: true,
          priority: 'default',
          notifyOn: 'completion,error',
          metadata: {
            multi_agent: {
              agents: [
                { name: 'research', role: 'research' },
                { name: 'execute', role: 'execute' },
              ],
            },
          },
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
          lastRun: null,
          nextRun: null,
        },
        isLoading: false,
        refetch: vi.fn(),
      })

      mockUseTaskExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      })
    })

    it('renders multi-agent UI components', async () => {
      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        expect(screen.getByTestId('multi-agent-progress')).toBeInTheDocument()
        expect(screen.getByTestId('agent-output-viewer')).toBeInTheDocument()
      })
    })

    it('initializes agents with pending status', async () => {
      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        const progressComponent = screen.getByTestId('multi-agent-progress')
        expect(progressComponent).toHaveTextContent('research: pending')
        expect(progressComponent).toHaveTextContent('execute: pending')
      })
    })

    it('still shows execution history', async () => {
      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        expect(screen.getByText('Execution History')).toBeInTheDocument()
      })
    })
  })

  describe('WebSocket Event Handling', () => {
    let mockSubscribe: any

    beforeEach(() => {
      mockSubscribe = vi.fn(() => vi.fn())
      mockUseWebSocket.mockReturnValue({
        subscribe: mockSubscribe,
        isConnected: true,
      })

      mockUseTask.mockReturnValue({
        data: {
          id: 'test-task-id',
          name: 'Multi-Agent Task',
          description: 'Multi-agent test',
          command: 'test-command',
          args: '',
          schedule: '0 0 * * *',
          enabled: true,
          priority: 'default',
          notifyOn: 'completion,error',
          metadata: {
            multi_agent: {
              agents: [
                { name: 'research', role: 'research' },
                { name: 'execute', role: 'execute' },
              ],
            },
          },
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
          lastRun: null,
          nextRun: null,
        },
        isLoading: false,
        refetch: vi.fn(),
      })

      mockUseTaskExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      })
    })

    it('subscribes to agent events', () => {
      render(<TaskDetailPage />, { wrapper })

      expect(mockSubscribe).toHaveBeenCalledWith('agent_started', expect.any(Function))
      expect(mockSubscribe).toHaveBeenCalledWith('agent_completed', expect.any(Function))
      expect(mockSubscribe).toHaveBeenCalledWith('agent_failed', expect.any(Function))
    })

    it('updates agent status on agent_started event', async () => {
      let agentStartedHandler: any

      mockSubscribe.mockImplementation((eventType: string, handler: any) => {
        if (eventType === 'agent_started') {
          agentStartedHandler = handler
        }
        return vi.fn()
      })

      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        expect(screen.getByTestId('multi-agent-progress')).toBeInTheDocument()
      })

      // Trigger agent_started event
      agentStartedHandler({
        type: 'agent_started',
        data: { agent_name: 'research', timestamp: '2024-01-01T00:00:00Z' },
      })

      await waitFor(() => {
        const progressComponent = screen.getByTestId('multi-agent-progress')
        expect(progressComponent).toHaveTextContent('research: running')
      })
    })

    it('updates agent status on agent_completed event', async () => {
      let agentCompletedHandler: any

      mockSubscribe.mockImplementation((eventType: string, handler: any) => {
        if (eventType === 'agent_completed') {
          agentCompletedHandler = handler
        }
        return vi.fn()
      })

      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        expect(screen.getByTestId('multi-agent-progress')).toBeInTheDocument()
      })

      // Trigger agent_completed event
      agentCompletedHandler({
        type: 'agent_completed',
        data: {
          agent_name: 'research',
          output: { structured: { result: 'success' }, narrative: 'Done' },
          timestamp: '2024-01-01T00:00:00Z',
        },
      })

      await waitFor(() => {
        const progressComponent = screen.getByTestId('multi-agent-progress')
        expect(progressComponent).toHaveTextContent('research: completed')
      })
    })

    it('updates agent status on agent_failed event', async () => {
      let agentFailedHandler: any

      mockSubscribe.mockImplementation((eventType: string, handler: any) => {
        if (eventType === 'agent_failed') {
          agentFailedHandler = handler
        }
        return vi.fn()
      })

      render(<TaskDetailPage />, { wrapper })

      await waitFor(() => {
        expect(screen.getByTestId('multi-agent-progress')).toBeInTheDocument()
      })

      // Trigger agent_failed event
      agentFailedHandler({
        type: 'agent_failed',
        data: {
          agent_name: 'execute',
          error: 'Command failed',
          timestamp: '2024-01-01T00:00:00Z',
        },
      })

      await waitFor(() => {
        const progressComponent = screen.getByTestId('multi-agent-progress')
        expect(progressComponent).toHaveTextContent('execute: failed')
      })
    })
  })

  describe('Loading State', () => {
    it('shows skeleton when task is loading', () => {
      mockUseTask.mockReturnValue({
        data: null,
        isLoading: true,
        refetch: vi.fn(),
      })

      mockUseTaskExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      })

      render(<TaskDetailPage />, { wrapper })

      // Check for skeleton elements
      const skeletons = document.querySelectorAll('.animate-pulse')
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('Error State', () => {
    it('shows error message when task not found', () => {
      mockUseTask.mockReturnValue({
        data: null,
        isLoading: false,
        refetch: vi.fn(),
      })

      mockUseTaskExecutions.mockReturnValue({
        data: [],
        isLoading: false,
        refetch: vi.fn(),
      })

      render(<TaskDetailPage />, { wrapper })

      expect(screen.getByText('Task not found')).toBeInTheDocument()
      expect(screen.getByText("The task you're looking for doesn't exist")).toBeInTheDocument()
    })
  })
})
