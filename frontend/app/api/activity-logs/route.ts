import { NextRequest, NextResponse } from "next/server"
import { auth } from "@/lib/auth"
import { prisma } from "@/lib/prisma"

export async function GET(request: NextRequest) {
  try {
    // Auth check
    const session = await auth()
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    // Parse query params
    const searchParams = request.nextUrl.searchParams
    const limit = parseInt(searchParams.get("limit") || "50")
    const type = searchParams.get("type") || undefined
    const executionId = searchParams.get("executionId") || undefined

    // Build where clause
    const where: any = {}
    if (type) {
      where.type = type
    }
    if (executionId) {
      where.executionId = executionId
    }

    // Query database
    const logs = await prisma.activityLog.findMany({
      where: Object.keys(where).length > 0 ? where : undefined,
      orderBy: { createdAt: "desc" },
      take: limit,
    })

    return NextResponse.json(logs)
  } catch (error) {
    console.error("Error fetching activity logs:", error)
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  }
}
