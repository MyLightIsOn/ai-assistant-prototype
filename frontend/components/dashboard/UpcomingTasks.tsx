"use client"

import { useEffect, useMemo } from "react"
import { useTasks } from "@/lib/hooks/useTasks"
import { useWebSocket } from "@/lib/hooks/useWebSocket"
import { useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle, ArrowRight, Clock, Play } from "lucide-react"
import { formatDistanceToNow, cn } from "@/lib/utils"
import { taskKeys } from "@/lib/hooks/useTasks"
import Link from "next/link"
import { Task } from "@/lib/types/api"

export function UpcomingTasks() {
  const queryClient = useQueryClient()
  const { data: tasks, isLoading, error } = useTasks()
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true })

  // WebSocket integration for real-time updates
  useEffect(() => {
    if (!isConnected) return

    const unsubscribe = subscribe("*", (message) => {
      const { type } = message

      // Invalidate tasks when relevant events occur
      if (
        type === "execution_start" ||
        type === "execution_complete" ||
        type === "status_update"
      ) {
        queryClient.invalidateQueries({ queryKey: taskKeys.all })
      }
    })

    return unsubscribe
  }, [isConnected, subscribe, queryClient])

  // Get next 5 upcoming tasks (enabled, has nextRun, sorted by nextRun)
  const upcomingTasks = useMemo(() => {
    if (!tasks) return []

    return tasks
      .filter(task => task.enabled && task.nextRun)
      .sort((a, b) => {
        const dateA = new Date(a.nextRun!).getTime()
        const dateB = new Date(b.nextRun!).getTime()
        return dateA - dateB
      })
      .slice(0, 5)
  }, [tasks])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Upcoming Tasks</CardTitle>
          <CardDescription>Next 5 scheduled task runs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center justify-between gap-4">
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
                <Skeleton className="h-8 w-20" />
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
          <CardTitle>Upcoming Tasks</CardTitle>
          <CardDescription>Next 5 scheduled task runs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">
              Failed to load tasks
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
            <CardTitle>Upcoming Tasks</CardTitle>
            <CardDescription>Next 5 scheduled task runs</CardDescription>
          </div>
          <Link href="/tasks">
            <Button variant="ghost" size="sm">
              View All
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {upcomingTasks.length === 0 ? (
          <div className="flex items-center justify-center py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No upcoming tasks scheduled
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {upcomingTasks.map((task) => (
              <UpcomingTaskItem key={task.id} task={task} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface UpcomingTaskItemProps {
  task: Task
}

function UpcomingTaskItem({ task }: UpcomingTaskItemProps) {
  const nextRunDate = new Date(task.nextRun!)
  const now = new Date()
  const minutesUntil = Math.floor((nextRunDate.getTime() - now.getTime()) / 60000)
  const isImminent = minutesUntil < 60

  return (
    <Link href={`/tasks/${task.id}`}>
      <div
        className={cn(
          "flex items-center justify-between gap-4 rounded-lg border p-3 transition-colors hover:bg-accent/50",
          isImminent && "border-yellow-300 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950"
        )}
      >
        <div className="flex-1 overflow-hidden">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium truncate">{task.name}</p>
            {task.priority !== "default" && (
              <Badge
                variant={
                  task.priority === "urgent"
                    ? "destructive"
                    : task.priority === "high"
                    ? "default"
                    : "secondary"
                }
                className="text-xs"
              >
                {task.priority}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
            <Clock className="h-3 w-3" />
            <span>{formatDistanceToNow(nextRunDate)}</span>
            {isImminent && (
              <Badge variant="outline" className="text-xs text-yellow-700 dark:text-yellow-300">
                Soon
              </Badge>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={(e) => {
            e.preventDefault()
            // TODO: Implement manual trigger
          }}
        >
          <Play className="h-4 w-4" />
          <span className="sr-only">Run task</span>
        </Button>
      </div>
    </Link>
  )
}
