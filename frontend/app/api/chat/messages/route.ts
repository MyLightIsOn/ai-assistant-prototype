import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const session = await auth();
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Parse query parameters
    const { searchParams } = new URL(request.url);
    const limitParam = searchParams.get('limit');
    const offsetParam = searchParams.get('offset');

    // Validate and apply defaults
    let limit = limitParam ? parseInt(limitParam, 10) : 50;
    const offset = offsetParam ? parseInt(offsetParam, 10) : 0;

    // Enforce max limit
    if (limit > 200) {
      limit = 200;
    }

    // Fetch messages and total count in parallel
    const [messages, total] = await Promise.all([
      prisma.chatMessage.findMany({
        orderBy: { createdAt: 'desc' },
        take: limit,
        skip: offset,
        include: { attachments: true },
      }),
      prisma.chatMessage.count(),
    ]);

    // Transform messages to response format
    const transformedMessages = messages
      .reverse() // Reverse to chronological order (oldest first)
      .map((msg) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        messageType: msg.messageType,
        metadata: msg.message_metadata
          ? typeof msg.message_metadata === 'string'
            ? JSON.parse(msg.message_metadata)
            : msg.message_metadata
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
