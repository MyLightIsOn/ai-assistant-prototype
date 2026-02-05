"use client"

import { useParams, useRouter } from "next/navigation"
import { useTask } from "@/lib/hooks/useTasks"
import { useTaskExecutions } from "@/lib/hooks/useTaskExecutions"
import { useWebSocket } from "@/lib/hooks/useWebSocket"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge"
import { MultiAgentProgress, Agent } from "@/components/executions/MultiAgentProgress"
import { AgentOutputViewer, AgentOutput } from "@/components/executions/AgentOutputViewer"
import {
  ChevronLeft,
  Edit,
  Play,
  Calendar,
  Clock,
  Terminal,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react"
import { toast } from "sonner"
import { useEffect, useState } from "react"
import { formatDistanceToNow } from "@/lib/utils"
import type {
  AgentStartedMessage,
  AgentCompletedMessage,
  AgentFailedMessage
} from "@/lib/types/api"

export default function TaskDetailPage() {
  const params = useParams()
  const router = useRouter()
  const taskId = params.id as string

  const { data: task, isLoading: taskLoading, refetch: refetchTask } = useTask(taskId)
  const { data: executions, isLoading: executionsLoading, refetch: refetchExecutions } = useTaskExecutions(taskId)
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true })

  // Multi-agent state
  const [agents, setAgents] = useState<Agent[]>([])
  const [agentOutputs, setAgentOutputs] = useState<AgentOutput[]>([])

  // Detect if this is a multi-agent task
  const isMultiAgent = task?.metadata?.multi_agent !== undefined
  const multiAgentConfig = task?.metadata?.multi_agent

  // Initialize agents from config when task loads
  useEffect(() => {
    if (multiAgentConfig) {
      const initialAgents: Agent[] = multiAgentConfig.agents.map(agent => ({
        name: agent.name,
        status: 'pending',
        role: agent.role as Agent['role']
      }))
      setAgents(initialAgents)

      const initialOutputs: AgentOutput[] = multiAgentConfig.agents.map(agent => ({
        agentName: agent.name,
        status: 'pending'
      }))
      setAgentOutputs(initialOutputs)
    }
  }, [multiAgentConfig])

  // Subscribe to WebSocket updates
  useEffect(() => {
    if (!isConnected) return

    const unsubscribe = subscribe('execution_complete', (message) => {
      const data = message.data as { executionId: string; taskId: string }
      if (data.taskId === taskId) {
        refetchTask()
        refetchExecutions()
      }
    })

    const unsubscribeStatus = subscribe('status_update', () => {
      refetchTask()
      refetchExecutions()
    })

    // Agent event handlers
    const unsubscribeAgentStarted = subscribe('agent_started', (message) => {
      const data = (message.data as AgentStartedMessage['data'])
      setAgents(prev => prev.map(agent =>
        agent.name === data.agent_name
          ? { ...agent, status: 'running' }
          : agent
      ))
      setAgentOutputs(prev => prev.map(output =>
        output.agentName === data.agent_name
          ? { ...output, status: 'running' }
          : output
      ))
    })

    const unsubscribeAgentCompleted = subscribe('agent_completed', (message) => {
      const data = (message.data as AgentCompletedMessage['data'])
      setAgents(prev => prev.map(agent =>
        agent.name === data.agent_name
          ? { ...agent, status: 'completed' }
          : agent
      ))
      setAgentOutputs(prev => prev.map(output =>
        output.agentName === data.agent_name
          ? {
              ...output,
              status: 'completed',
              structuredOutput: data.output.structured,
              narrativeOutput: data.output.narrative
            }
          : output
      ))
    })

    const unsubscribeAgentFailed = subscribe('agent_failed', (message) => {
      const data = (message.data as AgentFailedMessage['data'])
      setAgents(prev => prev.map(agent =>
        agent.name === data.agent_name
          ? { ...agent, status: 'failed' }
          : agent
      ))
      setAgentOutputs(prev => prev.map(output =>
        output.agentName === data.agent_name
          ? { ...output, status: 'failed' }
          : output
      ))
      toast.error(`Agent ${data.agent_name} failed: ${data.error}`)
    })

    return () => {
      unsubscribe()
      unsubscribeStatus()
      unsubscribeAgentStarted()
      unsubscribeAgentCompleted()
      unsubscribeAgentFailed()
    }
  }, [isConnected, subscribe, taskId, refetchTask, refetchExecutions])

  const handleTrigger = async () => {
    try {
      const response = await fetch(`/api/tasks/${taskId}/trigger`, {
        method: 'POST',
      })

      if (!response.ok) {
        throw new Error('Failed to trigger task')
      }

      toast.success('Task triggered successfully')
      refetchExecutions()
    } catch (error) {
      toast.error('Failed to trigger task')
      console.error(error)
    }
  }

  if (taskLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
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
          The task you're looking for doesn't exist
        </p>
        <Button onClick={() => router.push('/tasks')}>
          <ChevronLeft className="mr-2 h-4 w-4" />
          Back to Tasks
        </Button>
      </div>
    )
  }

  const priorityColors = {
    urgent: 'destructive',
    high: 'default',
    default: 'secondary',
    low: 'outline',
  } as const

  const getExecutionStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-600" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
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
            <h1 className="text-3xl font-bold tracking-tight">{task.name}</h1>
            <p className="text-muted-foreground">
              {task.description || "No description"}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={handleTrigger} variant="outline">
            <Play className="mr-2 h-4 w-4" />
            Run Now
          </Button>
          <Button onClick={() => router.push(`/tasks/${taskId}/edit`)}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Task Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <TaskStatusBadge status="idle" />
              <Badge
                variant={
                  priorityColors[task.priority as keyof typeof priorityColors] ||
                  'secondary'
                }
              >
                {task.priority}
              </Badge>
              <Badge variant={task.enabled ? 'default' : 'outline'}>
                {task.enabled ? 'Enabled' : 'Disabled'}
              </Badge>
            </div>

            <div className="space-y-3 text-sm">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Command:</span>
                <code className="rounded bg-muted px-2 py-1 text-xs">
                  {task.command} {task.args}
                </code>
              </div>

              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Schedule:</span>
                <code className="text-xs">{task.schedule}</code>
              </div>

              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Last run:</span>
                <span className="text-xs">
                  {task.lastRun
                    ? formatDistanceToNow(new Date(task.lastRun))
                    : 'Never'}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Next run:</span>
                <span className="text-xs">
                  {task.nextRun && task.enabled
                    ? formatDistanceToNow(new Date(task.nextRun))
                    : 'Not scheduled'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Notification Settings</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Notify on:</span>
                <p className="text-muted-foreground mt-1">
                  {task.notifyOn
                    .split(',')
                    .map((item) => item.trim())
                    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
                    .join(', ')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {isMultiAgent && agents.length > 0 && (
        <div className="space-y-6">
          <MultiAgentProgress agents={agents} />
          <AgentOutputViewer agents={agentOutputs} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Execution History</CardTitle>
          <CardDescription>
            Recent task executions and their status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {executionsLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : executions && executions.length > 0 ? (
            <div className="space-y-2">
              {executions.slice(0, 10).map((execution) => (
                <div
                  key={execution.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex items-center gap-3">
                    {getExecutionStatusIcon(execution.status)}
                    <div>
                      <p className="text-sm font-medium">
                        {execution.status.charAt(0).toUpperCase() +
                          execution.status.slice(1)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(execution.startedAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    {execution.duration ? (
                      <span>{(execution.duration / 1000).toFixed(2)}s</span>
                    ) : (
                      <span>Running...</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Clock className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No executions yet</p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleTrigger}
                className="mt-4"
              >
                <Play className="mr-2 h-4 w-4" />
                Run your first execution
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
