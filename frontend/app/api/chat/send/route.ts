import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

const MAX_CONTENT_LENGTH = 50000

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

    // Parse request body with error handling
    let body: SendMessageRequest
    try {
      body = await request.json()
    } catch {
      return NextResponse.json(
        { error: 'Invalid JSON in request body' },
        { status: 400 }
      )
    }

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

    if (body.content.length > MAX_CONTENT_LENGTH) {
      return NextResponse.json(
        { error: `content must be at most ${MAX_CONTENT_LENGTH} characters` },
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
    if (body.attachments && Array.isArray(body.attachments)) {
      // Validate array length
      if (body.attachments.length > 10) {
        return NextResponse.json(
          { error: 'Maximum 10 attachments allowed' },
          { status: 400 }
        )
      }

      for (const attachmentId of body.attachments) {
        // Validate attachment ID is string
        if (typeof attachmentId !== 'string') {
          continue // Skip invalid IDs
        }

        const attachment = await prisma.chatAttachment.findUnique({
          where: { id: attachmentId },
        })

        // Only link if attachment exists and not already linked
        if (attachment && !attachment.messageId) {
          try {
            await prisma.chatAttachment.update({
              where: { id: attachmentId },
              data: { messageId: userMessage.id },
            })
          } catch {
            // Attachment might have been deleted, continue with others
            console.error(`Failed to link attachment ${attachmentId}`)
          }
        }
      }
    }

    // Trigger Python backend execution (non-blocking)
    const backendUrl = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000'

    // Fire and forget - don't await
    // Call /api/chat/execute (not /api/chat/send) since message is already created
    fetch(`${backendUrl}/api/chat/execute`, {
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
