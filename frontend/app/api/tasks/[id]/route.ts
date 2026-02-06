import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { updateTaskSchema } from "@/lib/validations/task";
import { z } from "zod";

/**
 * GET /api/tasks/[id]
 * Get a single task by ID
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const { id } = await params;

    const task = await prisma.task.findFirst({
      where: {
        id: id,
        userId: session.user.id,
      },
      include: {
        executions: {
          orderBy: { startedAt: "desc" },
          take: 10,
        },
      },
    });

    if (!task) {
      return NextResponse.json(
        { error: "Task not found" },
        { status: 404 }
      );
    }

    return NextResponse.json(task);
  } catch (error) {
    console.error("Error fetching task:", error);
    return NextResponse.json(
      { error: "Failed to fetch task" },
      { status: 500 }
    );
  }
}

/**
 * PATCH /api/tasks/[id]
 * Update a task
 */
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const { id } = await params;

    // Verify task exists and belongs to user
    const existingTask = await prisma.task.findFirst({
      where: {
        id: id,
        userId: session.user.id,
      },
    });

    if (!existingTask) {
      return NextResponse.json(
        { error: "Task not found" },
        { status: 404 }
      );
    }

    const body = await request.json();

    // Validate request body
    const validatedData = updateTaskSchema.parse(body);

    // Update task in database
    const task = await prisma.task.update({
      where: { id: id },
      data: {
        ...validatedData,
        // Serialize metadata object to JSON string for SQLite storage
        metadata: validatedData.metadata ? JSON.stringify(validatedData.metadata) : undefined,
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
      // Don't fail the request if sync fails
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
      // Non-blocking - task still updated
    }

    return NextResponse.json(task);
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Validation failed", details: error.issues },
        { status: 422 }
      );
    }

    console.error("Error updating task:", error);
    return NextResponse.json(
      { error: "Failed to update task" },
      { status: 500 }
    );
  }
}

/**
 * DELETE /api/tasks/[id]
 * Delete a task
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const { id } = await params;

    // Verify task exists and belongs to user
    const existingTask = await prisma.task.findFirst({
      where: {
        id: id,
        userId: session.user.id,
      },
    });

    if (!existingTask) {
      return NextResponse.json(
        { error: "Task not found" },
        { status: 404 }
      );
    }

    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

    // Delete Calendar event first (non-blocking)
    try {
      await fetch(`${backendUrl}/api/calendar/sync/${id}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Calendar delete failed:", error);
      // Non-blocking - proceed with task deletion
    }

    // Delete task (cascade will handle executions and logs)
    await prisma.task.delete({
      where: { id: id },
    });

    // Remove from APScheduler via Python backend
    try {
      await fetch(`${backendUrl}/api/scheduler/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId: id }),
      });
    } catch (syncError) {
      console.error("Failed to remove from scheduler:", syncError);
      // Don't fail the request if sync fails
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting task:", error);
    return NextResponse.json(
      { error: "Failed to delete task" },
      { status: 500 }
    );
  }
}
