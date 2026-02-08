import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

interface SendMessageRequest {
  content: string
  attachments?: string[]
}

/**
 * POST /api/chat/send
 * Send chat message and trigger AI execution
 */
export async function POST(request: NextRequest) {
  try {
    const session = await auth()

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Parse request body
    const body: SendMessageRequest = await request.json()

    // Validate content
    if (!body.content || typeof body.content !== 'string') {
      return NextResponse.json(
        { error: 'content is required and must be a string' },
        { status: 400 }
      )
    }

    if (body.content.length < 1) {
      return NextResponse.json(
        { error: 'content must be at least 1 character' },
        { status: 400 }
      )
    }

    if (body.content.length > 50000) {
      return NextResponse.json(
        { error: 'content must be at most 50000 characters' },
        { status: 400 }
      )
    }

    // Create user message in database
    const userMessage = await prisma.chatMessage.create({
      data: {
        userId: session.user.id,
        role: 'user',
        content: body.content,
        messageType: 'text',
      },
    })

    // Link attachments if provided
    if (body.attachments && body.attachments.length > 0) {
      for (const attachmentId of body.attachments) {
        const attachment = await prisma.chatAttachment.findUnique({
          where: { id: attachmentId },
        })

        if (attachment) {
          await prisma.chatAttachment.update({
            where: { id: attachmentId },
            data: { messageId: userMessage.id },
          })
        }
      }
    }

    // Trigger Python backend execution (non-blocking)
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

    // Fire and forget - don't await
    fetch(`${backendUrl}/api/chat/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        userId: session.user.id,
        userMessageId: userMessage.id,
        content: body.content,
      }),
    }).catch((error) => {
      console.error('Failed to trigger backend execution:', error)
      // Non-blocking - message still saved
    })

    return NextResponse.json({
      messageId: userMessage.id,
    })
  } catch (error) {
    console.error('Error sending chat message:', error)
    return NextResponse.json(
      { error: 'Failed to send message' },
      { status: 500 }
    )
  }
}
