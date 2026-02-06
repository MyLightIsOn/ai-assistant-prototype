import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

/**
 * POST /api/tasks/[id]/trigger
 * Manually trigger a task execution
 */
export async function POST(
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

    // Trigger task execution via Python backend
    try {
      const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";
      const response = await fetch(`${backendUrl}/api/tasks/${id}/execute`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorDetail = await response.text();
        return NextResponse.json(
          {
            error: `Failed to trigger task (Backend returned ${response.status})`,
            backendStatus: response.status,
            detail: errorDetail
          },
          { status: 503 }
        );
      }

      const data = await response.json();
      return NextResponse.json(data);
    } catch (backendError) {
      console.error("Failed to trigger task execution:", backendError);
      return NextResponse.json(
        {
          error: "Failed to trigger task execution. Backend may be offline.",
          detail: backendError instanceof Error ? backendError.message : String(backendError)
        },
        { status: 503 }
      );
    }
  } catch (error) {
    console.error("Error triggering task:", error);
    return NextResponse.json(
      { error: "Failed to trigger task" },
      { status: 500 }
    );
  }
}
