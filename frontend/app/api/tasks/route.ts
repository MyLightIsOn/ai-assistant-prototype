import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { createTaskSchema } from "@/lib/validations/task";
import { z } from "zod";

/**
 * GET /api/tasks
 * List all tasks for the authenticated user
 */
export async function GET() {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const tasks = await prisma.task.findMany({
      where: { userId: session.user.id },
      orderBy: { createdAt: "desc" },
      include: {
        executions: {
          take: 1,
          orderBy: { startedAt: "desc" },
        },
      },
    });

    // Parse metadata JSON strings (SQLite stores as string, not JSON type)
    const tasksWithParsedMetadata = tasks.map(task => ({
      ...task,
      metadata: task.metadata && typeof task.metadata === 'string'
        ? JSON.parse(task.metadata)
        : task.metadata  // If already object (e.g., after Prisma upgrade), use as-is
    }));

    return NextResponse.json({ tasks: tasksWithParsedMetadata });
  } catch (error) {
    console.error("Error fetching tasks:", error);
    return NextResponse.json(
      { error: "Failed to fetch tasks" },
      { status: 500 }
    );
  }
}

/**
 * POST /api/tasks
 * Create a new task
 */
export async function POST(request: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const body = await request.json();

    // Validate request body
    const validatedData = createTaskSchema.parse(body);

    // Create task in database
    const task = await prisma.task.create({
      data: {
        ...validatedData,
        userId: session.user.id,
        // Serialize metadata object to JSON string for SQLite storage
        metadata: validatedData.metadata ? JSON.stringify(validatedData.metadata) : null,
      },
    });

    // Sync with APScheduler via Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
    try {
      await fetch(`${backendUrl}/api/scheduler/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: task.id }),
      });
    } catch (syncError) {
      console.error("Failed to sync with scheduler:", syncError);
      // Don't fail the request if sync fails - scheduler will sync on restart
    }

    // Trigger Calendar sync (non-blocking)
    try {
      await fetch(`${backendUrl}/api/calendar/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: task.id }),
      });
    } catch (error) {
      console.error("Calendar sync failed:", error);
      // Non-blocking - task still created
    }

    return NextResponse.json({ task }, { status: 201 });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Validation failed", details: error.issues },
        { status: 422 }
      );
    }

    console.error("Error creating task:", error);
    return NextResponse.json(
      { error: "Failed to create task" },
      { status: 500 }
    );
  }
}
