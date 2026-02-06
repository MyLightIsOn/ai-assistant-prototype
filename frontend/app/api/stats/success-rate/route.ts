import { NextRequest, NextResponse } from "next/server"

/**
 * GET /api/stats/success-rate
 *
 * Proxy endpoint to fetch task success rate statistics from Python backend.
 * Queries TaskExecution records and calculates success rate for specified time period.
 *
 * Query Parameters:
 *   - days: Number of days to calculate success rate for (1-365, default: 7)
 *
 * Returns:
 *   {
 *     success_rate: number,      // Percentage (0-100)
 *     total_executions: number,  // Total executions in period
 *     successful: number,        // Count of successful executions
 *     failed: number,            // Count of failed executions
 *     period_days: number        // Number of days queried
 *   }
 */
export async function GET(request: NextRequest) {
  try {
    // Extract query parameter
    const searchParams = request.nextUrl.searchParams
    const days = searchParams.get("days") || "7"

    // Validate days parameter
    const daysNum = parseInt(days, 10)
    if (isNaN(daysNum) || daysNum < 1 || daysNum > 365) {
      return NextResponse.json(
        { error: "Invalid days parameter. Must be between 1 and 365." },
        { status: 400 }
      )
    }

    // Forward request to Python backend
    const backendUrl = process.env.PYTHON_BACKEND_URL || "http://localhost:8000"
    const response = await fetch(
      `${backendUrl}/api/stats/success-rate?days=${daysNum}`,
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
        { error: "Failed to fetch success rate from backend" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error fetching success rate:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
