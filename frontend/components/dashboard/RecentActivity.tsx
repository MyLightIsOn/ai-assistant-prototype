"use client"

import { useEffect } from "react"
import { useActivityLogs } from "@/lib/hooks/useActivityLogs"
import { useWebSocket } from "@/lib/hooks/useWebSocket"
import { useQueryClient } from "@tanstack/react-query"
import { ActivityLogItem } from "@/components/activity/ActivityLogItem"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, ArrowRight } from "lucide-react"
import { activityLogKeys } from "@/lib/hooks/useActivityLogs"
import Link from "next/link"

export function RecentActivity() {
  const queryClient = useQueryClient()
  const { data: logs, isLoading, error } = useActivityLogs({ limit: 10 })
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true })

  // WebSocket integration for real-time updates
  useEffect(() => {
    if (!isConnected) return

    const unsubscribe = subscribe("*", (message) => {
      const { type } = message

      // Invalidate activity logs when relevant events occur
      if (
        type === "execution_start" ||
        type === "execution_complete" ||
        type === "status_update" ||
        type === "error"
      ) {
        queryClient.invalidateQueries({ queryKey: activityLogKeys.all })
      }
    })

    return unsubscribe
  }, [isConnected, subscribe, queryClient])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest events and task executions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest events and task executions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">
              Failed to load activity logs
            </p>
            <p className="text-xs text-muted-foreground">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest events and task executions</CardDescription>
          </div>
          <Link href="/activity">
            <Button variant="ghost" size="sm">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {!logs || logs.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No activity to display
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {logs.slice(0, 10).map((log) => (
              <ActivityLogItem key={log.id} log={log} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
