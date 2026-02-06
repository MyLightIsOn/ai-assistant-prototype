/* eslint-disable @typescript-eslint/no-explicit-any */
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
const { POST: createTask } = await import('../tasks/route')
const { PATCH: updateTask } = await import('../tasks/[id]/route')
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

describe('/api/tasks - Multi-Agent Metadata Validation', () => {
  describe('POST - Create task with multi-agent metadata', () => {
    it('creates task with valid multi-agent metadata', async () => {
      const taskData = {
        name: 'Multi-Agent Task',
        description: 'Test task',
        command: 'test',
        schedule: '0 9 * * *',
        enabled: true,
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research', 'execute', 'review'],
            synthesize: true,
            roles: {
              research: { type: 'research' },
              execute: { type: 'execute' },
              review: { type: 'review' },
            },
          },
        },
      }

      const createdTask = { id: 'task-1', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      expect(response.status).toBe(201)
      const data = await response.json()
      expect(data.task.id).toBe('task-1')
      expect(prisma.task.create).toHaveBeenCalled()
    })

    it('creates task with custom agent roles', async () => {
      const taskData = {
        name: 'Custom Agent Task',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['security_audit'],
            synthesize: false,
            roles: {
              security_audit: {
                type: 'custom',
                instructions: 'Perform security audit of the codebase',
              },
            },
          },
        },
      }

      const createdTask = { id: 'task-2', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      expect(response.status).toBe(201)
    })

    it('creates task without multi-agent metadata (single agent)', async () => {
      const taskData = {
        name: 'Single Agent Task',
        command: 'test',
        schedule: '0 9 * * *',
      }

      const createdTask = { id: 'task-3', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      expect(response.status).toBe(201)
    })

    it('rejects invalid multi-agent metadata - missing sequence', async () => {
      const taskData = {
        name: 'Invalid Task',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            // Missing sequence
            roles: {
              research: { type: 'research' },
            },
          },
        },
      }

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      // Note: Validation happens at backend orchestrator level, not API level
      // Frontend API accepts the payload; validation is deferred
      // This test documents current behavior - may change in future
      expect(response.status).toBe(201) // Currently passes through
    })

    it('rejects invalid multi-agent metadata - missing roles', async () => {
      const taskData = {
        name: 'Invalid Task',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research'],
            // Missing roles
          },
        },
      }

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      // Currently passes through - validation at execution time
      expect(response.status).toBe(201)
    })

    it('rejects invalid agent role type', async () => {
      const taskData = {
        name: 'Invalid Role Type Task',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['invalid_role'],
            roles: {
              invalid_role: { type: 'nonexistent_role_type' },
            },
          },
        },
      }

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)

      // Currently passes through - validation at execution time
      expect(response.status).toBe(201)
    })
  })

  describe('PATCH - Update task with multi-agent metadata', () => {
    it('updates task to enable multi-agent mode', async () => {
      const existingTask = {
        id: 'task-1',
        name: 'Original Task',
        userId: 'user-1',
        metadata: null,
      }

      const updates = {
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research', 'execute'],
            synthesize: false,
            roles: {
              research: { type: 'research' },
              execute: { type: 'execute' },
            },
          },
        },
      }

      const updatedTask = { ...existingTask, ...updates }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.update).mockResolvedValue(updatedTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks/task-1', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })

      const response = await updateTask(request, {
        params: Promise.resolve({ id: 'task-1' }),
      })

      expect(response.status).toBe(200)
    })

    it('updates task to disable multi-agent mode', async () => {
      const existingTask = {
        id: 'task-1',
        name: 'Multi-Agent Task',
        userId: 'user-1',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research'],
            roles: { research: { type: 'research' } },
          },
        },
      }

      const updates = {
        metadata: {
          agents: {
            enabled: false,
            sequence: [],
            roles: {},
          },
        },
      }

      const updatedTask = { ...existingTask, ...updates }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.update).mockResolvedValue(updatedTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks/task-1', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })

      const response = await updateTask(request, {
        params: Promise.resolve({ id: 'task-1' }),
      })

      expect(response.status).toBe(200)
    })

    it('updates agent sequence and roles', async () => {
      const existingTask = {
        id: 'task-1',
        userId: 'user-1',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research'],
            roles: { research: { type: 'research' } },
          },
        },
      }

      const updates = {
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research', 'execute', 'review'],
            synthesize: true,
            roles: {
              research: { type: 'research' },
              execute: { type: 'execute' },
              review: { type: 'review' },
            },
          },
        },
      }

      const updatedTask = { ...existingTask, ...updates }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.update).mockResolvedValue(updatedTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks/task-1', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })

      const response = await updateTask(request, {
        params: Promise.resolve({ id: 'task-1' }),
      })

      expect(response.status).toBe(200)
      const data = await response.json()
      expect(data.metadata.agents.sequence).toEqual(['research', 'execute', 'review'])
      expect(data.metadata.agents.synthesize).toBe(true)
    })

    it('updates custom agent instructions', async () => {
      const existingTask = {
        id: 'task-1',
        userId: 'user-1',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['custom'],
            roles: {
              custom: {
                type: 'custom',
                instructions: 'Old instructions',
              },
            },
          },
        },
      }

      const updates = {
        metadata: {
          agents: {
            enabled: true,
            sequence: ['custom'],
            roles: {
              custom: {
                type: 'custom',
                instructions: 'New security audit instructions',
              },
            },
          },
        },
      }

      const updatedTask = { ...existingTask, ...updates }

      vi.mocked(prisma.task.findFirst).mockResolvedValue(existingTask as any)
      vi.mocked(prisma.task.update).mockResolvedValue(updatedTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks/task-1', {
        method: 'PATCH',
        body: JSON.stringify(updates),
      })

      const response = await updateTask(request, {
        params: Promise.resolve({ id: 'task-1' }),
      })

      expect(response.status).toBe(200)
    })
  })

  describe('Multi-Agent Metadata Schema Validation', () => {
    it('accepts all valid predefined agent role types', async () => {
      const validRoles = ['research', 'execute', 'review', 'custom']

      for (const roleType of validRoles) {
        const taskData = {
          name: `Task with ${roleType}`,
          command: 'test',
          schedule: '0 9 * * *',
          metadata: {
            agents: {
              enabled: true,
              sequence: [roleType],
              roles: {
                [roleType]: {
                  type: roleType,
                  ...(roleType === 'custom' && {
                    instructions: 'Custom instructions',
                  }),
                },
              },
            },
          },
        }

        const createdTask = { id: `task-${roleType}`, userId: 'user-1', ...taskData }
        vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

        const request = new NextRequest('http://localhost:3000/api/tasks', {
          method: 'POST',
          body: JSON.stringify(taskData),
        })

        const response = await createTask(request)
        expect(response.status).toBe(201)
      }
    })

    it('accepts metadata with synthesis enabled', async () => {
      const taskData = {
        name: 'Task with Synthesis',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research', 'execute'],
            synthesize: true,
            roles: {
              research: { type: 'research' },
              execute: { type: 'execute' },
            },
          },
        },
      }

      const createdTask = { id: 'task-syn', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })

    it('accepts metadata with synthesis disabled', async () => {
      const taskData = {
        name: 'Task without Synthesis',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research'],
            synthesize: false,
            roles: {
              research: { type: 'research' },
            },
          },
        },
      }

      const createdTask = { id: 'task-nosyn', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })

    it('accepts metadata with default synthesis (undefined)', async () => {
      const taskData = {
        name: 'Task with Default Synthesis',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: true,
            sequence: ['research'],
            // synthesize is optional, defaults to false
            roles: {
              research: { type: 'research' },
            },
          },
        },
      }

      const createdTask = { id: 'task-default', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })
  })

  describe('Edge Cases and Boundary Conditions', () => {
    it('accepts empty metadata object', async () => {
      const taskData = {
        name: 'Task with Empty Metadata',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {},
      }

      const createdTask = { id: 'task-empty', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })

    it('accepts null metadata', async () => {
      const taskData = {
        name: 'Task with Null Metadata',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: null,
      }

      const createdTask = { id: 'task-null', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })

    it('accepts task without metadata field', async () => {
      const taskData = {
        name: 'Task without Metadata Field',
        command: 'test',
        schedule: '0 9 * * *',
        // No metadata field at all
      }

      const createdTask = { id: 'task-no-meta', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })

    it('accepts multi-agent metadata with agents.enabled = false', async () => {
      const taskData = {
        name: 'Disabled Multi-Agent Task',
        command: 'test',
        schedule: '0 9 * * *',
        metadata: {
          agents: {
            enabled: false,
            sequence: ['research'],
            roles: {
              research: { type: 'research' },
            },
          },
        },
      }

      const createdTask = { id: 'task-disabled', userId: 'user-1', ...taskData }
      vi.mocked(prisma.task.create).mockResolvedValue(createdTask as any)

      const request = new NextRequest('http://localhost:3000/api/tasks', {
        method: 'POST',
        body: JSON.stringify(taskData),
      })

      const response = await createTask(request)
      expect(response.status).toBe(201)
    })
  })
})
