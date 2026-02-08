import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/chat/messages
 * Fetch chat message history for authenticated user
 *
 * Uses Prisma directly for read operation (hybrid pattern)
 */
export async function GET(request: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Parse query parameters
    const searchParams = request.nextUrl.searchParams;
    const limit = parseInt(searchParams.get("limit") || "50");
    const offset = parseInt(searchParams.get("offset") || "0");

    // Validate parameters
    if (limit < 1 || limit > 200) {
      return NextResponse.json(
        { error: "Limit must be between 1 and 200" },
        { status: 400 }
      );
    }

    if (offset < 0) {
      return NextResponse.json(
        { error: "Offset must be non-negative" },
        { status: 400 }
      );
    }

    // Fetch messages from database
    const messages = await prisma.chatMessage.findMany({
      where: { userId: session.user.id },
      orderBy: { createdAt: "desc" },
      skip: offset,
      take: limit,
      include: {
        attachments: true,
      },
    });

    // Get total count for pagination
    const total = await prisma.chatMessage.count({
      where: { userId: session.user.id },
    });

    // Convert to frontend format (reverse to chronological order)
    const messagesFormatted = messages.reverse().map((msg) => ({
      id: msg.id,
      role: msg.role,
      content: msg.content,
      messageType: msg.messageType,
      metadata: msg.metadata ?
        (typeof msg.metadata === 'string' ? JSON.parse(msg.metadata) : msg.metadata)
        : null,
      createdAt: msg.createdAt.getTime(),
      attachments: msg.attachments.map((att) => ({
        id: att.id,
        fileName: att.fileName,
        filePath: att.filePath,
        fileType: att.fileType,
        fileSize: att.fileSize,
      })),
    }));

    return NextResponse.json({
      messages: messagesFormatted,
      total,
    });
  } catch (error) {
    console.error("Error fetching chat messages:", error);
    return NextResponse.json(
      { error: "Failed to fetch messages" },
      { status: 500 }
    );
  }
}
