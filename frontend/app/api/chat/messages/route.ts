import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

const DEFAULT_MESSAGE_LIMIT = 50;
const MAX_MESSAGE_LIMIT = 200;

export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Parse query parameters with validation
    const { searchParams } = new URL(request.url);
    const limitParam = parseInt(searchParams.get('limit') || String(DEFAULT_MESSAGE_LIMIT), 10);
    const offsetParam = parseInt(searchParams.get('offset') || '0', 10);

    // Validate and sanitize
    const limit = Math.min(
      Math.max(1, isNaN(limitParam) ? DEFAULT_MESSAGE_LIMIT : limitParam),
      MAX_MESSAGE_LIMIT
    );
    const offset = Math.max(0, isNaN(offsetParam) ? 0 : offsetParam);

    // Fetch messages and total count in parallel
    const [messages, total] = await Promise.all([
      prisma.chatMessage.findMany({
        where: { userId: session.user.id },
        orderBy: { createdAt: 'desc' },
        skip: offset,
        take: limit,
        include: { attachments: true },
      }),
      prisma.chatMessage.count({ where: { userId: session.user.id } }),
    ]);

    // Transform messages to response format
    const transformedMessages = messages
      .reverse() // Reverse to chronological order (oldest first)
      .map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        messageType: msg.messageType,
        metadata: msg.metadata
          ? (() => {
              try {
                return typeof msg.metadata === 'string'
                  ? JSON.parse(msg.metadata)
                  : msg.metadata;
              } catch {
                return null; // Invalid JSON, return null
              }
            })()
          : null,
        createdAt:
          typeof msg.createdAt === 'number'
            ? msg.createdAt
            : msg.createdAt.getTime(),
        attachments: msg.attachments.map((att) => ({
          id: att.id,
          fileName: att.fileName,
          filePath: att.filePath,
          fileType: att.fileType,
          fileSize: att.fileSize,
        })),
      }));

    return NextResponse.json({
      messages: transformedMessages,
      total,
    });
  } catch (error) {
    console.error('Error fetching chat messages:', error);
    return NextResponse.json(
      { error: 'Failed to fetch messages' },
      { status: 500 }
    );
  }
}
