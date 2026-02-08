/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Prisma
vi.mock('@/lib/prisma', () => ({
  prisma: {
    chatMessage: {
      create: vi.fn(),
    },
    chatAttachment: {
      findUnique: vi.fn(),
      update: vi.fn(),
    },
  },
}))

// Mock auth
vi.mock('@/lib/auth', () => ({
  auth: vi.fn(),
}))

// Mock fetch for Python backend
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({ messageId: 'msg-123' }),
  } as Response)
) as any

// Import after mocks
const { POST: sendMessage } = await import('../chat/send/route')
const { prisma } = await import('@/lib/prisma')
const { auth } = await import('@/lib/auth')

beforeEach(() => {
  vi.clearAllMocks()
  // Default: authenticated user
  vi.mocked(auth).mockResolvedValue({
    user: { id: 'user-1', email: 'test@example.com' },
  } as any)
})

describe('/api/chat/send', () => {
  describe('POST', () => {
    it('returns 401 if not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null)

      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: 'Hello' }),
      })
      const response = await sendMessage(request)
      const data = await response.json()

      expect(response.status).toBe(401)
      expect(data.error).toBe('Unauthorized')
    })

    it('validates required content field', async () => {
      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ attachments: [] }),
      })
      const response = await sendMessage(request)
      const data = await response.json()

      expect(response.status).toBe(400)
      expect(data.error).toContain('content')
    })

    it('validates content length (min 1 char)', async () => {
      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: '' }),
      })
      const response = await sendMessage(request)

      expect(response.status).toBe(400)
    })

    it('validates content length (max 50000 chars)', async () => {
      const longContent = 'a'.repeat(50001)
      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: longContent }),
      })
      const response = await sendMessage(request)

      expect(response.status).toBe(400)
    })

    it('creates user message in database', async () => {
      const mockMessage = {
        id: 'msg-new',
        userId: 'user-1',
        role: 'user',
        content: 'Hello AI',
        messageType: 'text',
        message_metadata: null,
        createdAt: new Date('2026-02-08T10:00:00Z'),
      }

      vi.mocked(prisma.chatMessage.create).mockResolvedValue(mockMessage as any)

      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: 'Hello AI', attachments: [] }),
      })
      const response = await sendMessage(request)
      const data = await response.json()

      expect(response.status).toBe(200)
      expect(data.messageId).toBe('msg-new')
      expect(prisma.chatMessage.create).toHaveBeenCalledWith({
        data: {
          userId: 'user-1',
          role: 'user',
          content: 'Hello AI',
          messageType: 'text',
        },
      })
    })

    it('links attachments to message', async () => {
      const mockMessage = {
        id: 'msg-new',
        userId: 'user-1',
        role: 'user',
        content: 'File attached',
        messageType: 'text',
        message_metadata: null,
        createdAt: new Date(),
      }

      const mockAttachment = {
        id: 'att-1',
        messageId: null,
        fileName: 'test.txt',
        filePath: '/uploads/test.txt',
        fileType: 'text',
        fileSize: 1024,
      }

      vi.mocked(prisma.chatMessage.create).mockResolvedValue(mockMessage as any)
      vi.mocked(prisma.chatAttachment.findUnique).mockResolvedValue(mockAttachment as any)

      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: 'File attached', attachments: ['att-1'] }),
      })
      await sendMessage(request)

      expect(prisma.chatAttachment.findUnique).toHaveBeenCalledWith({
        where: { id: 'att-1' },
      })
      expect(prisma.chatAttachment.update).toHaveBeenCalledWith({
        where: { id: 'att-1' },
        data: { messageId: 'msg-new' },
      })
    })

    it('triggers Python backend execution via fetch', async () => {
      const mockMessage = {
        id: 'msg-new',
        userId: 'user-1',
        role: 'user',
        content: 'Execute task',
        messageType: 'text',
        message_metadata: null,
        createdAt: new Date(),
      }

      vi.mocked(prisma.chatMessage.create).mockResolvedValue(mockMessage as any)

      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: 'Execute task', attachments: [] }),
      })
      await sendMessage(request)

      // Verify backend was called (with timeout for background task)
      await new Promise(resolve => setTimeout(resolve, 100))

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/chat/send',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId: 'user-1',
            userMessageId: 'msg-new',
            content: 'Execute task',
          }),
        })
      )
    })

    it('returns success even if backend call fails (non-blocking)', async () => {
      const mockMessage = {
        id: 'msg-new',
        userId: 'user-1',
        role: 'user',
        content: 'Hello',
        messageType: 'text',
        message_metadata: null,
        createdAt: new Date(),
      }

      vi.mocked(prisma.chatMessage.create).mockResolvedValue(mockMessage as any)
      vi.mocked(global.fetch as any).mockRejectedValue(new Error('Backend down'))

      const request = new NextRequest('http://localhost:3000/api/chat/send', {
        method: 'POST',
        body: JSON.stringify({ content: 'Hello', attachments: [] }),
      })
      const response = await sendMessage(request)

      expect(response.status).toBe(200)
    })
  })
})
