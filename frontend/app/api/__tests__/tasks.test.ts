import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Prisma - use factory function to avoid hoisting issues
vi.mock('@/lib/prisma', () => ({
  prisma: {
    task: {
      findMany: vi.fn(),
      findFirst: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}))

// Mock auth - use factory function
vi.mock('@/lib/auth', () => ({
  auth: vi.fn(),
}))

// Import after mocks are set up
const { GET: getTasks, POST: createTask } = await import('../tasks/route')
const { GET: getTask, PATCH: updateTask, DELETE: deleteTask } = await import('../tasks/[id]/route')
const { prisma } = await import('@/lib/prisma')
const { auth } = await import('@/lib/auth')

// Mock fetch for backend sync calls
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  } as Response)
) as any

beforeEach(() => {
  vi.clearAllMocks()
  // Default: authenticated user
  vi.mocked(auth).mockResolvedValue({
    user: { id: 'user-1', email: 'test@example.com' },
  } as any)
})

describe('/api/tasks', () => {
  describe('GET', () => {
    it('returns all tasks for authenticated user', async () => {
      const mockTasks = [
        { id: '1', name: 'Task 1', enabled: true, userId: 'user-1', executions: [], metadata: null },
        { id: '2', name: 'Task 2', enabled: false, userId: 'user-1', executions: [], metadata: null },
      ]

      vi.mocked(prisma.task.findMany).mockResolvedValue(mockTasks as any)

      const response = await getTasks()

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data).toEqual({ tasks: mockTasks })
      expect(prisma.task.findMany).toHaveBeenCalledWith({
        where: { userId: 'user-1' },
        orderBy: { createdAt: 'desc' },
        include: {
          executions: {
            take: 1,
            orderBy: { startedAt: 'desc' },
          },
        },
      })
    })

    it('returns 401 when not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const response = await getTasks()

      expect(response.status).toBe(401)
      const data = await response.json()
      expect(data.error).toBe('Unauthorized')
    })

    it('returns 500 on database error', async () => {
      vi.mocked(prisma.task.findMany).mockRejectedValue(new Error('DB Error'))

      const response = await getTasks()

      expect(response.status).toBe(500)
      const data = await response.json()
      expect(data.error).toBe('Failed to fetch tasks')
    })
  })

  describe('POST', () => {
    it('creates new task with valid data', async () => {
      const newTask = {
        name: 'New Task',
        description: 'Description',
        command: 'run-task',
        schedule: '0 9 * * *',
        enabled: true,
      }

      const createdTask = { id: 'task-1', userId: 'user-1', ...newTask }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(newTask),
      })

      const response = await createTask(request)

      expect(response.status).toBe(201)
      const data = await response.json()
      expect(data.task.id).toBe('task-1')
      expect(prisma.task.create).toHaveBeenCalled()
    })

    it('returns 422 for invalid data', async () => {
      const invalidTask = { name: '' } // Missing required fields

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(invalidTask),
      })

      const response = await createTask(request)

      expect(response.status).toBe(422)
      const data = await response.json()
      expect(data.error).toBe('Validation failed')
    })

    it('validates cron expression format', async () => {
      const invalidCron = {
        name: 'Task',
        command: 'run-task',
        schedule: 'invalid-cron',
      }

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(invalidCron),
      })

      const response = await createTask(request)

      expect(response.status).toBe(422)
      const data = await response.json()
      expect(data.error).toBe('Validation failed')
    })

    it('returns 401 when not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify({ name: 'Task' }),
      })

      const response = await createTask(request)

      expect(response.status).toBe(401)
    })
  })
})

describe('/api/tasks/[id]', () => {
  describe('GET', () => {
    it('returns task by id', async () => {
      const mockTask = {
        id: 'task-1',
        name: 'Task 1',
        userId: 'user-1',
        executions: [],
      }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(mockTask as any)

      const response = await getTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1'),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.id).toBe('task-1')
    })

    it('returns 404 when task not found', async () => {
      vi.mocked(prisma.task.findFirst).mockResolvedValue(null)

      const response = await getTask(
        new NextRequest('http://localhost:3000/api/tasks/invalid'),
        { params: Promise.resolve({ id: 'invalid' }) }
      )

      expect(response.status).toBe(404)
      const data = await response.json()
      expect(data.error).toBe('Task not found')
    })

    it('returns 401 when not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const response = await getTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1'),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(401)
    })
  })

  describe('PATCH', () => {
    it('updates task with valid data', async () => {
      const existingTask = { id: 'task-1', name: 'Old', userId: 'user-1' }
      const updates = { name: 'Updated Task', enabled: false }
      const updatedTask = { ...existingTask, ...updates }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.update).mockResolvedValue(updatedTask as any)

      const response = await updateTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1', {
          method: 'PATCH',
          body: JSON.stringify(updates),
        }),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.name).toBe('Updated Task')
    })

    it('returns 404 when updating non-existent task', async () => {
      vi.mocked(prisma.task.findFirst).mockResolvedValue(null)

      const response = await updateTask(
        new NextRequest('http://localhost:3000/api/tasks/invalid', {
          method: 'PATCH',
          body: JSON.stringify({ name: 'Updated' }),
        }),
        { params: Promise.resolve({ id: 'invalid' }) }
      )

      expect(response.status).toBe(404)
      const data = await response.json()
      expect(data.error).toBe('Task not found')
    })

    it('returns 422 for invalid update data', async () => {
      const existingTask = { id: 'task-1', userId: 'user-1' }
      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)

      const response = await updateTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1', {
          method: 'PATCH',
          body: JSON.stringify({ schedule: 'invalid-cron' }),
        }),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(422)
    })

    it('returns 401 when not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const response = await updateTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1', {
          method: 'PATCH',
          body: JSON.stringify({ name: 'Updated' }),
        }),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(401)
    })
  })

  describe('DELETE', () => {
    it('deletes task successfully', async () => {
      const existingTask = { id: 'task-1', userId: 'user-1' }
      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.delete).mockResolvedValue(existingTask as any)

      const response = await deleteTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1', {
          method: 'DELETE',
        }),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.success).toBe(true)
    })

    it('returns 404 when deleting non-existent task', async () => {
      vi.mocked(prisma.task.findFirst).mockResolvedValue(null)

      const response = await deleteTask(
        new NextRequest('http://localhost:3000/api/tasks/invalid', {
          method: 'DELETE',
        }),
        { params: Promise.resolve({ id: 'invalid' }) }
      )

      expect(response.status).toBe(404)
      const data = await response.json()
      expect(data.error).toBe('Task not found')
    })

    it('returns 401 when not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const response = await deleteTask(
        new NextRequest('http://localhost:3000/api/tasks/task-1', {
          method: 'DELETE',
        }),
        { params: Promise.resolve({ id: 'task-1' }) }
      )

      expect(response.status).toBe(401)
    })
  })
})
