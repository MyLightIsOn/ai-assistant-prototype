import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { renderWithQueryClient } from '../test-utils'
import { TaskForm } from '@/components/tasks/TaskForm'
import type { Task } from '@/lib/types/api'

const mockTask: Task = {
  id: 'task-1',
  userId: 'user-1',
  name: 'Test Task',
  description: 'Test description',
  schedule: '0 9 * * *',
  enabled: true,
  command: 'claude',
  args: 'test args',
  priority: 'default',
  notifyOn: 'completion,error',
  createdAt: new Date('2024-01-01').toISOString(),
  updatedAt: new Date('2024-01-01').toISOString(),
  lastRun: null,
  nextRun: null,
}

// Create mock functions
const mockPush = vi.fn()
const mockBack = vi.fn()
const mockCreateMutateAsync = vi.fn()
const mockUpdateMutateAsync = vi.fn()

// Mock the router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    back: mockBack,
    replace: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}))

// Mock the hooks
vi.mock('@/lib/hooks/useTasks', () => ({
  useCreateTask: () => ({
    mutateAsync: mockCreateMutateAsync,
    isPending: false,
  }),
  useUpdateTask: () => ({
    mutateAsync: mockUpdateMutateAsync,
    isPending: false,
  }),
}))

describe('TaskForm', () => {
  beforeEach(() => {
    mockPush.mockClear()
    mockBack.mockClear()
    mockCreateMutateAsync.mockClear()
    mockUpdateMutateAsync.mockClear()
    mockCreateMutateAsync.mockResolvedValue({ id: 'new-task-id' })
    mockUpdateMutateAsync.mockResolvedValue({})
  })

  it('renders empty form for new task', () => {
    renderWithQueryClient(<TaskForm />)

    expect(screen.getByLabelText(/task name/i)).toHaveValue('')
    expect(screen.getByLabelText(/description/i)).toHaveValue('')
    expect(screen.getByRole('button', { name: /create task/i })).toBeInTheDocument()
  })

  it('renders form with task data for editing', () => {
    renderWithQueryClient(<TaskForm task={mockTask} mode="edit" />)

    expect(screen.getByLabelText(/task name/i)).toHaveValue('Test Task')
    expect(screen.getByLabelText(/description/i)).toHaveValue('Test description')
    expect(screen.getByRole('button', { name: /update task/i })).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    renderWithQueryClient(<TaskForm />)

    const submitButton = screen.getByRole('button', { name: /create task/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/task name is required/i)).toBeInTheDocument()
    })
  })

  it('submits form with valid data for create', async () => {
    renderWithQueryClient(<TaskForm />)

    await userEvent.type(screen.getByLabelText(/task name/i), 'New Task')
    await userEvent.type(screen.getByLabelText(/description/i), 'Task description')
    await userEvent.type(screen.getByLabelText(/^command$/i), 'claude')

    const submitButton = screen.getByRole('button', { name: /create task/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(mockCreateMutateAsync).toHaveBeenCalled()
    })
  })

  it('submits form with valid data for update', async () => {
    renderWithQueryClient(<TaskForm task={mockTask} mode="edit" />)

    const nameInput = screen.getByLabelText(/task name/i)
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Updated Task')

    const submitButton = screen.getByRole('button', { name: /update task/i })
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(mockUpdateMutateAsync).toHaveBeenCalledWith({
        id: 'task-1',
        data: expect.objectContaining({
          name: 'Updated Task',
        }),
      })
    })
  })

  it('shows loading state during submission', async () => {
    mockCreateMutateAsync.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    )

    renderWithQueryClient(<TaskForm />)

    await userEvent.type(screen.getByLabelText(/task name/i), 'Test Task')
    await userEvent.type(screen.getByLabelText(/^command$/i), 'claude')

    const submitButton = screen.getByRole('button', { name: /create task/i })
    await userEvent.click(submitButton)

    // Check for loading spinner
    await waitFor(() => {
      const svg = document.querySelector('svg.animate-spin')
      expect(svg).toBeInTheDocument()
    })
  })

  it('toggles enabled checkbox', async () => {
    renderWithQueryClient(<TaskForm />)

    const enabledSwitch = screen.getByRole('switch', { name: /enable task/i })
    expect(enabledSwitch).toBeChecked()

    await userEvent.click(enabledSwitch)
    expect(enabledSwitch).not.toBeChecked()
  })

  it('has cancel button that is clickable', async () => {
    renderWithQueryClient(<TaskForm />)

    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    expect(cancelButton).toBeInTheDocument()
    expect(cancelButton).not.toBeDisabled()
  })

  it('displays all form sections', () => {
    renderWithQueryClient(<TaskForm />)

    expect(screen.getByText('Basic Information')).toBeInTheDocument()
    expect(screen.getByText('Command Configuration')).toBeInTheDocument()
    expect(screen.getByText('Schedule')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('includes priority and notification settings', () => {
    renderWithQueryClient(<TaskForm />)

    expect(screen.getByText('Priority')).toBeInTheDocument()
    expect(screen.getByText('Notifications')).toBeInTheDocument()
  })
})
