import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { renderWithQueryClient } from '../test-utils'
import { TaskCard } from '@/components/tasks/TaskCard'
import type { Task } from '@/lib/types/api'

const mockTask: Task = {
  id: 'task-1',
  name: 'Test Task',
  description: 'Test description',
  schedule: '0 9 * * *',
  enabled: true,
  command: 'claude',
  args: 'test',
  priority: 'default',
  createdAt: new Date('2024-01-01').toISOString(),
  updatedAt: new Date('2024-01-01').toISOString(),
  lastRun: null,
  nextRun: null,
}

// Create mock functions that will be shared
const mockPush = vi.fn()
const mockUpdateMutateAsync = vi.fn()
const mockDeleteMutateAsync = vi.fn()

// Mock the router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock the hooks
vi.mock('@/lib/hooks/useTasks', () => ({
  useUpdateTask: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
  useDeleteTask: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
}))

describe('TaskCard', () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockUpdateMutateAsync.mockClear()
    mockDeleteMutateAsync.mockClear()
    mockUpdateMutateAsync.mockResolvedValue({})
    mockDeleteMutateAsync.mockResolvedValue({})
  })

  it('renders task information', () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    expect(screen.getByText('Test Task')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
    expect(screen.getByText(/0 9 \* \* \*/)).toBeInTheDocument()
  })

  it('shows enabled switch when task is enabled', () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const switchElement = screen.getByRole('switch', { name: /disable task/i })
    expect(switchElement).toBeChecked()
  })

  it('shows disabled switch when task is disabled', () => {
    const disabledTask = { ...mockTask, enabled: false }
    renderWithQueryClient(<TaskCard task={disabledTask} />)

    const switchElement = screen.getByRole('switch', { name: /enable task/i })
    expect(switchElement).not.toBeChecked()
  })

  it('shows action menu with options', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    expect(screen.getByText('View Details')).toBeInTheDocument()
    expect(screen.getByText('Run Now')).toBeInTheDocument()
    expect(screen.getByText('Edit')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('shows view details menu item', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    expect(screen.getByText('View Details')).toBeInTheDocument()
  })

  it('shows edit menu item', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    expect(screen.getByText('Edit')).toBeInTheDocument()
  })

  it('shows delete confirmation dialog when delete clicked', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    const deleteItem = screen.getByText('Delete')
    await userEvent.click(deleteItem)

    expect(screen.getByText('Delete Task')).toBeInTheDocument()
    expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
  })

  it('calls delete mutation when confirmed', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    const deleteItem = screen.getByText('Delete')
    await userEvent.click(deleteItem)

    const confirmButton = screen.getByRole('button', { name: /delete/i })
    await userEvent.click(confirmButton)

    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith('task-1')
    })
  })

  it('triggers task when run now clicked', async () => {
    const mockOnTrigger = vi.fn()
    renderWithQueryClient(<TaskCard task={mockTask} onTrigger={mockOnTrigger} />)

    const menuButton = screen.getByRole('button', { name: /open menu/i })
    await userEvent.click(menuButton)

    const runNowItem = screen.getByText('Run Now')
    await userEvent.click(runNowItem)

    expect(mockOnTrigger).toHaveBeenCalledWith('task-1')
  })

  it('toggles enabled state when switch clicked', async () => {
    renderWithQueryClient(<TaskCard task={mockTask} />)

    const switchElement = screen.getByRole('switch')
    await userEvent.click(switchElement)

    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
        id: 'task-1',
        data: { enabled: false },
      })
    })
  })
})
