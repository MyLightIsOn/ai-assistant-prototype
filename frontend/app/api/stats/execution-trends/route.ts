import { NextRequest, NextResponse } from "next/server"

/**
 * GET /api/stats/execution-trends
 *
 * Proxy endpoint to fetch daily execution trend data from Python backend.
 * Returns execution counts grouped by date for visualization in charts.
 *
 * Query Parameters:
 *   - days: Number of days to query (1-30, default: 7)
 *
 * Returns:
 *   [
 *     {
 *       date: string,        // ISO date string (YYYY-MM-DD)
 *       successful: number,  // Count of successful executions
 *       failed: number,      // Count of failed executions
 *       total: number        // Total executions for the day
 *     },
 *     ...
 *   ]
 *
 * Notes:
 *   - Returns continuous data with zeros for days with no executions
 *   - Data is sorted by date in ascending order (oldest first)
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameter
    const searchParams = request.nextUrl.searchParams
    const days = searchParams.get("days") || "7"

    // Validate days parameter
    const daysNum = parseInt(days, 10)
    if (isNaN(daysNum) || daysNum < 1 || daysNum > 30) {
      return NextResponse.json(
        { error: "Invalid days parameter. Must be between 1 and 30." },
        { status: 400 }
      )
    }

    // Forward request to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000"
    const response = await fetch(
      `${backendUrl}/api/stats/execution-trends?days=${daysNum}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      console.error("Backend error:", errorText)
      return NextResponse.json(
        { error: "Failed to fetch execution trends from backend" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error fetching execution trends:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
