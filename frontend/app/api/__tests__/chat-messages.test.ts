/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

// Mock Prisma - use factory function to avoid hoisting issues
vi.mock('@/lib/prisma', () => ({
  prisma: {
    chatMessage: {
      findMany: vi.fn(),
      count: vi.fn(),
    },
  },
}));

// Mock auth - use factory function
vi.mock('@/lib/auth', () => ({
  auth: vi.fn(),
}));

// Import after mocks are set up
const { GET: getMessages } = await import('../chat/messages/route');
const { prisma } = await import('@/lib/prisma');
const { auth } = await import('@/lib/auth');

describe('/api/chat/messages', () => {
  describe('GET', () => {
    beforeEach(() => {
      vi.clearAllMocks();
      // Default: authenticated user
      vi.mocked(auth).mockResolvedValue({
        user: { id: 'user-1', email: 'test@example.com' },
      } as any);
    });

    it('returns 401 if not authenticated', async () => {
      vi.mocked(auth).mockResolvedValue(null as any);

      const request = new NextRequest('http://localhost:3000/api/chat/messages');
      const response = await getMessages(request);

      expect(response.status).toBe(401);
      const data = await response.json();
      expect(data.error).toBe('Unauthorized');
    });

    it('returns messages for authenticated user', async () => {
      // Mock returns desc order (newest first) as Prisma would
      const mockMessages = [
        {
          id: 'msg-2',
          userId: 'user-1',
          role: 'assistant' as const,
          content: 'Hi there',
          messageType: 'text' as const,
          metadata: JSON.stringify({ model: 'claude-3' }),
          createdAt: new Date('2024-01-01T10:01:00Z'),
          attachments: [],
        },
        {
          id: 'msg-1',
          userId: 'user-1',
          role: 'user' as const,
          content: 'Hello',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:00:00Z'),
          attachments: [],
        },
      ];

      vi.mocked(prisma.chatMessage.findMany).mockResolvedValue(mockMessages as any);
      vi.mocked(prisma.chatMessage.count).mockResolvedValue(2);

      const request = new NextRequest('http://localhost:3000/api/chat/messages');
      const response = await getMessages(request);

      expect(response.status).toBe(200);
      const data = await response.json();

      expect(data.messages).toHaveLength(2);
      expect(data.total).toBe(2);
      expect(data.messages[0].id).toBe('msg-1');
      expect(data.messages[1].id).toBe('msg-2');
      expect(data.messages[1].metadata).toEqual({ model: 'claude-3' });
    });

    it('supports limit and offset query parameters', async () => {
      const mockMessages = [
        {
          id: 'msg-3',
          userId: 'user-1',
          role: 'user' as const,
          content: 'Message 3',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:02:00Z'),
          attachments: [],
        },
      ];

      vi.mocked(prisma.chatMessage.findMany).mockResolvedValue(mockMessages as any);
      vi.mocked(prisma.chatMessage.count).mockResolvedValue(10);

      const request = new NextRequest(
        'http://localhost:3000/api/chat/messages?limit=1&offset=2'
      );
      const response = await getMessages(request);

      expect(response.status).toBe(200);
      const data = await response.json();

      expect(prisma.chatMessage.findMany).toHaveBeenCalledWith({
        where: { userId: 'user-1' },
        orderBy: { createdAt: 'desc' },
        skip: 2,
        take: 1,
        include: { attachments: true },
      });
      expect(data.messages).toHaveLength(1);
      expect(data.total).toBe(10);
    });

    it('returns messages in chronological order (oldest first)', async () => {
      // Mock DB returns desc order (newest first)
      const mockMessages = [
        {
          id: 'msg-3',
          userId: 'user-1',
          role: 'assistant' as const,
          content: 'Third',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:02:00Z'),
          attachments: [],
        },
        {
          id: 'msg-2',
          userId: 'user-1',
          role: 'user' as const,
          content: 'Second',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:01:00Z'),
          attachments: [],
        },
        {
          id: 'msg-1',
          userId: 'user-1',
          role: 'user' as const,
          content: 'First',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:00:00Z'),
          attachments: [],
        },
      ];

      vi.mocked(prisma.chatMessage.findMany).mockResolvedValue(mockMessages as any);
      vi.mocked(prisma.chatMessage.count).mockResolvedValue(3);

      const request = new NextRequest('http://localhost:3000/api/chat/messages');
      const response = await getMessages(request);

      expect(response.status).toBe(200);
      const data = await response.json();

      // Response should be in chronological order (oldest first)
      expect(data.messages[0].id).toBe('msg-1');
      expect(data.messages[1].id).toBe('msg-2');
      expect(data.messages[2].id).toBe('msg-3');
      expect(data.messages[0].content).toBe('First');
      expect(data.messages[2].content).toBe('Third');
    });

    it('parses metadata JSON string to object', async () => {
      // Mock returns desc order (newest first) as Prisma would
      const mockMessages = [
        {
          id: 'msg-2',
          userId: 'user-1',
          role: 'user' as const,
          content: 'Question',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:01:00Z'),
          attachments: [],
        },
        {
          id: 'msg-1',
          userId: 'user-1',
          role: 'assistant' as const,
          content: 'Response',
          messageType: 'text' as const,
          metadata: JSON.stringify({ model: 'claude-3', tokens: 150 }),
          createdAt: new Date('2024-01-01T10:00:00Z'),
          attachments: [],
        },
      ];

      vi.mocked(prisma.chatMessage.findMany).mockResolvedValue(mockMessages as any);
      vi.mocked(prisma.chatMessage.count).mockResolvedValue(2);

      const request = new NextRequest('http://localhost:3000/api/chat/messages');
      const response = await getMessages(request);

      expect(response.status).toBe(200);
      const data = await response.json();

      expect(data.messages[0].metadata).toEqual({ model: 'claude-3', tokens: 150 });
      expect(data.messages[1].metadata).toBeNull();
    });

    it('includes attachment details in response', async () => {
      const mockMessages = [
        {
          id: 'msg-1',
          userId: 'user-1',
          role: 'user' as const,
          content: 'Check this file',
          messageType: 'text' as const,
          metadata: null,
          createdAt: new Date('2024-01-01T10:00:00Z'),
          attachments: [
            {
              id: 'att-1',
              fileName: 'document.pdf',
              filePath: '/uploads/document.pdf',
              fileType: 'application/pdf',
              fileSize: 1024000,
              messageId: 'msg-1',
              createdAt: new Date('2024-01-01T10:00:00Z'),
            },
            {
              id: 'att-2',
              fileName: 'image.png',
              filePath: '/uploads/image.png',
              fileType: 'image/png',
              fileSize: 512000,
              messageId: 'msg-1',
              createdAt: new Date('2024-01-01T10:00:00Z'),
            },
          ],
        },
      ];

      vi.mocked(prisma.chatMessage.findMany).mockResolvedValue(mockMessages as any);
      vi.mocked(prisma.chatMessage.count).mockResolvedValue(1);

      const request = new NextRequest('http://localhost:3000/api/chat/messages');
      const response = await getMessages(request);

      expect(response.status).toBe(200);
      const data = await response.json();

      expect(data.messages[0].attachments).toHaveLength(2);
      expect(data.messages[0].attachments[0]).toEqual({
        id: 'att-1',
        fileName: 'document.pdf',
        filePath: '/uploads/document.pdf',
        fileType: 'application/pdf',
        fileSize: 1024000,
      });
      expect(data.messages[0].attachments[1]).toEqual({
        id: 'att-2',
        fileName: 'image.png',
        filePath: '/uploads/image.png',
        fileType: 'image/png',
        fileSize: 512000,
      });
    });
  });
});
