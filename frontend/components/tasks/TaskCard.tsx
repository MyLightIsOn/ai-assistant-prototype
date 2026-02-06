"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Task } from "@/lib/types/api"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardAction,
  CardFooter,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { TaskStatusBadge } from "./TaskStatusBadge"
import { MultiAgentBadge } from "./MultiAgentBadge"
import {
  MoreVertical,
  Play,
  Edit,
  Trash2,
  Clock,
  Calendar,
  Terminal,
} from "lucide-react"
import { useUpdateTask, useDeleteTask } from "@/lib/hooks/useTasks"
import { toast } from "sonner"
import { formatDistanceToNow } from "@/lib/utils"

interface TaskCardProps {
  task: Task
  onTrigger?: (taskId: string) => void
}

export function TaskCard({ task, onTrigger }: TaskCardProps) {
  const router = useRouter()
  const updateTask = useUpdateTask()
  const deleteTask = useDeleteTask()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [isTogglingEnabled, setIsTogglingEnabled] = useState(false)

  const handleToggleEnabled = async (checked: boolean) => {
    setIsTogglingEnabled(true)
    try {
      await updateTask.mutateAsync({
        id: task.id,
        data: { enabled: checked },
      })
      toast.success(
        checked ? "Task enabled successfully" : "Task disabled successfully"
      )
    } catch (error) {
      toast.error("Failed to update task")
      console.error(error)
    } finally {
      setIsTogglingEnabled(false)
    }
  }

  const handleDelete = async () => {
    try {
      await deleteTask.mutateAsync(task.id)
      toast.success("Task deleted successfully")
      setDeleteDialogOpen(false)
    } catch (error) {
      toast.error("Failed to delete task")
      console.error(error)
    }
  }

  const handleTrigger = () => {
    if (onTrigger) {
      onTrigger(task.id)
    } else {
      toast.info("Manual trigger functionality will be available soon")
    }
  }

  const handleEdit = () => {
    router.push(`/tasks/${task.id}/edit`)
  }

  const handleViewDetails = () => {
    router.push(`/tasks/${task.id}`)
  }

  // Determine task status based on last execution
  const getTaskStatus = (): 'idle' | 'running' | 'success' | 'error' | 'pending' => {
    if (!task.lastRun) return 'idle'
    // This is simplified - in real implementation, check actual execution status
    return 'idle'
  }

  const priorityColors = {
    urgent: 'destructive',
    high: 'default',
    default: 'secondary',
    low: 'outline',
  } as const

  return (
    <>
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader>
          <CardAction>
            <div className="flex items-center gap-2">
              <Switch
                checked={task.enabled}
                onCheckedChange={handleToggleEnabled}
                disabled={isTogglingEnabled}
                aria-label={task.enabled ? "Disable task" : "Enable task"}
              />
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreVertical className="h-4 w-4" />
                    <span className="sr-only">Open menu</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleViewDetails}>
                    <Calendar className="mr-2 h-4 w-4" />
                    View Details
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleTrigger}>
                    <Play className="mr-2 h-4 w-4" />
                    Run Now
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleEdit}>
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setDeleteDialogOpen(true)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </CardAction>
          <div className="cursor-pointer" onClick={handleViewDetails}>
            <CardTitle>{task.name}</CardTitle>
            <CardDescription>
              {task.description || "No description provided"}
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <TaskStatusBadge status={getTaskStatus()} />
            <Badge
              variant={
                priorityColors[task.priority as keyof typeof priorityColors] ||
                'secondary'
              }
            >
              {task.priority}
            </Badge>
            {task.metadata?.multi_agent && (
              <MultiAgentBadge
                agentCount={task.metadata.multi_agent.agents.length}
                hasSynthesis={task.metadata.multi_agent.synthesis}
              />
            )}
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Terminal className="h-4 w-4" />
              <code className="rounded bg-muted px-2 py-1 text-xs">
                {task.command} {task.args}
              </code>
            </div>

            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span className="text-xs">Schedule: {task.schedule}</span>
            </div>
          </div>
        </CardContent>

        <CardFooter className="flex justify-between text-xs text-muted-foreground">
          <div>
            {task.lastRun ? (
              <span>
                Last run: {formatDistanceToNow(new Date(task.lastRun))}
              </span>
            ) : (
              <span>Never run</span>
            )}
          </div>
          <div>
            {task.nextRun && task.enabled ? (
              <span>
                Next run: {formatDistanceToNow(new Date(task.nextRun))}
              </span>
            ) : (
              <span>Not scheduled</span>
            )}
          </div>
        </CardFooter>
      </Card>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Task</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{task.name}&quot;? This action cannot
              be undone and will remove all execution history.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteTask.isPending}
            >
              {deleteTask.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
