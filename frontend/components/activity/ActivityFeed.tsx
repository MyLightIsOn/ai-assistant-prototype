"use client"

import { useState, useEffect } from "react"
import { useActivityLogs, useWebSocket } from "@/lib/hooks"
import { useQueryClient } from "@tanstack/react-query"
import { ActivityLogItem } from "./ActivityLogItem"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { activityLogKeys } from "@/lib/hooks/useActivityLogs"
import { AlertCircle, RefreshCw } from "lucide-react"

type LogFilter = "all" | "task_start" | "task_complete" | "error" | "notification_sent"

const INITIAL_LIMIT = 50
const LOAD_MORE_INCREMENT = 50

export function ActivityFeed() {
  const [filter, setFilter] = useState<LogFilter>("all")
  const [limit, setLimit] = useState(INITIAL_LIMIT)
  const queryClient = useQueryClient()

  // Fetch activity logs with current filter and limit
  const { data: logs, isLoading, error, refetch } = useActivityLogs({
    limit,
    ...(filter !== "all" && { type: filter }),
  })

  // WebSocket integration for real-time updates
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true })

  useEffect(() => {
    if (!isConnected) return

    // Subscribe to WebSocket messages for real-time updates
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

  const handleLoadMore = () => {
    setLimit((prev) => prev + LOAD_MORE_INCREMENT)
  }

  const handleFilterChange = (value: string) => {
    setFilter(value as LogFilter)
    setLimit(INITIAL_LIMIT) // Reset limit when changing filters
  }

  const handleRefresh = () => {
    refetch()
  }

  return (
    <div data-testid="activity-feed" className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl sm:text-2xl">Activity</CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={isLoading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
              <span className="sr-only">Refresh logs</span>
            </Button>
          </div>

          {/* Filter tabs */}
          <Tabs value={filter} onValueChange={handleFilterChange} className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="all" className="text-xs sm:text-sm">
                All
              </TabsTrigger>
              <TabsTrigger value="task_start" className="text-xs sm:text-sm">
                Tasks
              </TabsTrigger>
              <TabsTrigger value="task_complete" className="text-xs sm:text-sm">
                Complete
              </TabsTrigger>
              <TabsTrigger value="error" className="text-xs sm:text-sm">
                Errors
              </TabsTrigger>
              <TabsTrigger value="notification_sent" className="text-xs sm:text-sm">
                Notifications
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>

        <CardContent>
          {/* Loading state */}
          {isLoading && (
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
          )}

          {/* Error state */}
          {error && (
            <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-sm font-medium text-destructive">
                Failed to load activity logs
              </p>
              <p className="text-xs text-muted-foreground">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
              <Button variant="outline" size="sm" onClick={handleRefresh} className="mt-2">
                Try again
              </Button>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !error && logs?.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
              <p className="text-sm font-medium text-muted-foreground">
                No activity logs found
              </p>
              <p className="text-xs text-muted-foreground">
                {filter !== "all"
                  ? `No logs of type "${filter}" in the last 24 hours`
                  : "Activity will appear here as tasks are executed"}
              </p>
            </div>
          )}

          {/* Activity logs */}
          {!isLoading && !error && logs && logs.length > 0 && (
            <div className="space-y-3">
              {logs.map((log) => (
                <ActivityLogItem key={log.id} log={log} />
              ))}

              {/* Load more button */}
              {logs.length >= limit && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleLoadMore}
                    disabled={isLoading}
                  >
                    Load more
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* WebSocket connection indicator */}
          {!isConnected && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-200">
              <AlertCircle className="h-4 w-4" />
              <span>Real-time updates disconnected. Logs will update on refresh.</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

// Helper function for cn (already imported from utils)
function cn(...inputs: unknown[]) {
  return inputs.filter(Boolean).join(" ")
}
