"use client"

import { useParams, useRouter } from "next/navigation"
import { useTask } from "@/lib/hooks/useTasks"
import { TaskForm } from "@/components/tasks/TaskForm"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ChevronLeft, AlertCircle } from "lucide-react"

export default function EditTaskPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.id as string

  const { data: task, isLoading } = useTask(taskId)

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-2xl font-semibold mb-2">Task not found</h2>
        <p className="text-muted-foreground mb-4">
          The task you're trying to edit doesn't exist
        </p>
        <Button onClick={() => router.push('/tasks')}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Tasks
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.back()}
          className="gap-2"
        >
          <ChevronLeft className="h-4 w-4" />
          Back
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Edit Task</h1>
          <p className="text-muted-foreground">
            Update task configuration and schedule
          </p>
        </div>
      </div>

      <TaskForm task={task} mode="edit" />
    </div>
  )
}
