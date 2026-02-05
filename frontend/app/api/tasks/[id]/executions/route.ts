import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

/**
 * GET /api/tasks/[id]/executions
 * Get execution history for a task
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

    // Verify task exists and belongs to user
    const task = await prisma.task.findFirst({
      where: {
        id: id,
        userId: session.user.id,
      },
    });

    if (!task) {
      return NextResponse.json(
        { error: "Task not found" },
        { status: 404 }
      );
    }

    // Get executions for this task
    const executions = await prisma.taskExecution.findMany({
      where: {
        taskId: id,
      },
      orderBy: {
        startedAt: "desc",
      },
      take: 50, // Limit to last 50 executions
    });

    return NextResponse.json(executions);
  } catch (error) {
    console.error("Error fetching executions:", error);
    return NextResponse.json(
      { error: "Failed to fetch executions" },
      { status: 500 }
    );
  }
}
