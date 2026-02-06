import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { PrismaClient } from '@prisma/client'
import bcrypt from 'bcryptjs'
import path from 'path'

// Set DATABASE_URL to point to the correct database
process.env.DATABASE_URL = `file:${path.resolve(__dirname, '../..', 'ai-assistant.db')}`

const prisma = new PrismaClient()

describe('Prisma Database', () => {
  beforeAll(async () => {
    // Ensure we have a clean test environment
    await prisma.$connect()
  })

  afterAll(async () => {
    await prisma.$disconnect()
  })

  it('should connect to the database', async () => {
    // Test connection by querying the database
    const result = await prisma.$queryRaw`SELECT 1 as result`
    expect(result).toBeDefined()
  })

  describe('User Model', () => {
    it('should create a new user', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)

      const user = await prisma.user.create({
        data: {
          email: `test-${Date.now()}@example.com`,
          name: 'Test User',
          passwordHash,
        },
      })

      expect(user).toBeDefined()
      expect(user.id).toBeDefined()
      expect(user.email).toContain('test-')
      expect(user.name).toBe('Test User')
      expect(user.passwordHash).toBeDefined()
      expect(user.createdAt).toBeInstanceOf(Date)
      expect(user.updatedAt).toBeInstanceOf(Date)

      // Clean up
      await prisma.user.delete({ where: { id: user.id } })
    })

    it('should find user by email', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `findtest-${Date.now()}@example.com`

      // Create user
      const createdUser = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'Find Test User',
          passwordHash,
        },
      })

      // Find user
      const foundUser = await prisma.user.findUnique({
        where: { email: testEmail },
      })

      expect(foundUser).toBeDefined()
      expect(foundUser?.id).toBe(createdUser.id)
      expect(foundUser?.email).toBe(testEmail)

      // Clean up
      await prisma.user.delete({ where: { id: createdUser.id } })
    })

    it('should update user information', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `updatetest-${Date.now()}@example.com`

      // Create user
      const user = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'Original Name',
          passwordHash,
        },
      })

      // Update user
      const updatedUser = await prisma.user.update({
        where: { id: user.id },
        data: { name: 'Updated Name' },
      })

      expect(updatedUser.name).toBe('Updated Name')
      expect(updatedUser.updatedAt.getTime()).toBeGreaterThan(user.updatedAt.getTime())

      // Clean up
      await prisma.user.delete({ where: { id: user.id } })
    })

    it('should delete a user', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `deletetest-${Date.now()}@example.com`

      // Create user
      const user = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'Delete Test User',
          passwordHash,
        },
      })

      // Delete user
      await prisma.user.delete({ where: { id: user.id } })

      // Verify deletion
      const deletedUser = await prisma.user.findUnique({
        where: { id: user.id },
      })

      expect(deletedUser).toBeNull()
    })

    it('should enforce unique email constraint', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `uniquetest-${Date.now()}@example.com`

      // Create first user
      const user1 = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'First User',
          passwordHash,
        },
      })

      // Attempt to create second user with same email
      await expect(
        prisma.user.create({
          data: {
            email: testEmail,
            name: 'Second User',
            passwordHash,
          },
        })
      ).rejects.toThrow()

      // Clean up
      await prisma.user.delete({ where: { id: user1.id } })
    })
  })

  describe('Task Model', () => {
    it('should create a task with user relation', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `tasktest-${Date.now()}@example.com`

      // Create user
      const user = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'Task Test User',
          passwordHash,
        },
      })

      // Create task
      const task = await prisma.task.create({
        data: {
          userId: user.id,
          name: 'Test Task',
          description: 'A test task description',
          command: 'test-command',
          args: '{}',
          schedule: '0 8 * * *',
        },
      })

      expect(task).toBeDefined()
      expect(task.id).toBeDefined()
      expect(task.name).toBe('Test Task')
      expect(task.enabled).toBe(true)
      expect(task.priority).toBe('default')
      expect(task.notifyOn).toBe('completion,error')

      // Clean up
      await prisma.task.delete({ where: { id: task.id } })
      await prisma.user.delete({ where: { id: user.id } })
    })
  })

  describe('Session Model', () => {
    it('should create a session for a user', async () => {
      const passwordHash = await bcrypt.hash('testpassword', 10)
      const testEmail = `sessiontest-${Date.now()}@example.com`

      // Create user
      const user = await prisma.user.create({
        data: {
          email: testEmail,
          name: 'Session Test User',
          passwordHash,
        },
      })

      // Create session
      const expiresAt = new Date()
      expiresAt.setDate(expiresAt.getDate() + 30)

      const session = await prisma.session.create({
        data: {
          sessionToken: `test-token-${Date.now()}`,
          userId: user.id,
          expires: expiresAt,
        },
      })

      expect(session).toBeDefined()
      expect(session.id).toBeDefined()
      expect(session.sessionToken).toContain('test-token-')
      expect(session.userId).toBe(user.id)

      // Clean up
      await prisma.session.delete({ where: { id: session.id } })
      await prisma.user.delete({ where: { id: user.id } })
    })
  })
})
