import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

/**
 * DELETE /api/chat/clear
 * Clear all chat messages for authenticated user
 *
 * Proxies to Python backend (hybrid pattern - write operations go to Python)
 */
export async function DELETE(request: NextRequest) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Proxy to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

    const response = await fetch(`${backendUrl}/api/chat/clear`, {
      method: "DELETE",
      headers: {
        "Cookie": request.headers.get("cookie") || "",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend error: ${response.status}`, errorText);
      return NextResponse.json(
        {
          error: `Failed to clear messages (Backend returned ${response.status})`,
          detail: errorText,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error clearing chat:", error);

    // Check if backend is unreachable
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return NextResponse.json(
        {
          error: "Failed to clear messages. AI backend may be offline.",
          detail: "Please ensure the Python backend is running on port 8000",
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: "Failed to clear messages" },
      { status: 500 }
    );
  }
}
