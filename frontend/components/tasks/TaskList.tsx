"use client"

import { useTasks } from "@/lib/hooks/useTasks"
import { useWebSocketQuerySync } from "@/lib/hooks/useWebSocketQuerySync"
import { TaskCard } from "./TaskCard"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Inbox } from "lucide-react"
import { useRouter } from "next/navigation"

interface TaskListProps {
  onTriggerTask?: (taskId: string) => void
}

export function TaskList({ onTriggerTask }: TaskListProps) {
  const router = useRouter()
  const { data: tasks, isLoading, error, refetch } = useTasks()

  // Use WebSocket query sync for automatic refetching on task-related events
  useWebSocketQuerySync(
    ['tasks'],
    ['task_created', 'task_updated', 'task_deleted', 'task_status', 'scheduler_sync', 'status_update', 'execution_complete']
  )

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <p className="text-destructive mb-4">Failed to load tasks</p>
          <Button onClick={() => refetch()} variant="outline">
            Try Again
          </Button>
        </CardContent>
      </Card>
    )
  }

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <div className="p-6 space-y-4">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
              <div className="flex gap-2">
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-6 w-16" />
              </div>
            </div>
          </Card>
        ))}
      </div>
    )
  }

  if (!tasks || tasks.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <Inbox className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No tasks yet</h3>
          <p className="text-muted-foreground mb-4">
            Get started by creating your first scheduled task
          </p>
          <Button onClick={() => router.push('/tasks/new')}>
            <Plus className="mr-2 h-4 w-4" />
            Create your first task
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} onTrigger={onTriggerTask} />
      ))}
    </div>
  )
}
