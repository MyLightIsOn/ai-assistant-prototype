import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

/**
 * POST /api/chat/send
 * Send chat message and trigger AI execution
 *
 * Proxies to Python backend (hybrid pattern - write operations go to Python)
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

    // Parse request body
    const body = await request.json();

    // Validate input
    if (!body.content || typeof body.content !== 'string') {
      return NextResponse.json(
        { error: "Message content is required" },
        { status: 400 }
      );
    }

    if (body.content.length < 1 || body.content.length > 50000) {
      return NextResponse.json(
        { error: "Message content must be between 1 and 50,000 characters" },
        { status: 400 }
      );
    }

    // Proxy to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000";

    const response = await fetch(`${backendUrl}/api/chat/send`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Cookie": request.headers.get("cookie") || "",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend error: ${response.status}`, errorText);
      return NextResponse.json(
        {
          error: `Failed to send message (Backend returned ${response.status})`,
          detail: errorText,
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error sending chat message:", error);

    // Check if backend is unreachable
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return NextResponse.json(
        {
          error: "Failed to send message. AI backend may be offline.",
          detail: "Please ensure the Python backend is running on port 8000",
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      { error: "Failed to send message" },
      { status: 500 }
    );
  }
}
