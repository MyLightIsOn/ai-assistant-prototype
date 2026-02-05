"use client"

import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { useRouter } from "next/navigation"
import { TaskList } from "@/components/tasks/TaskList"
import { toast } from "sonner"

export default function TasksPage() {
  const router = useRouter()

  const handleTriggerTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}/trigger`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Failed to trigger task')
      }

      toast.success('Task triggered successfully')
    } catch (error) {
      toast.error('Failed to trigger task')
      console.error(error)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
          <p className="text-muted-foreground">
            Manage your scheduled AI tasks
          </p>
        </div>
        <Button onClick={() => router.push('/tasks/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Task
        </Button>
      </div>

      <TaskList onTriggerTask={handleTriggerTask} />
    </div>
  )
}
