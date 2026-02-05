"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"

export interface Agent {
  name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  role: 'research' | 'execute' | 'review' | 'custom'
}

export interface MultiAgentProgressProps {
  agents: Agent[]
  className?: string
}

export function MultiAgentProgress({ agents, className }: MultiAgentProgressProps) {
  // Calculate progress percentage based on completed agents
  const completedCount = agents.filter(agent => agent.status === 'completed').length
  const totalCount = agents.length
  const progressPercentage = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  // Get status icon and styling based on agent status
  const getStatusIcon = (status: Agent['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-600" />
      case 'pending':
        return <Circle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusVariant = (status: Agent['status']) => {
    switch (status) {
      case 'completed':
        return 'default'
      case 'running':
        return 'default'
      case 'failed':
        return 'destructive'
      case 'pending':
        return 'outline'
    }
  }

  const getStatusText = (status: Agent['status']) => {
    switch (status) {
      case 'completed':
        return 'Completed'
      case 'running':
        return 'Running'
      case 'failed':
        return 'Failed'
      case 'pending':
        return 'Pending'
    }
  }

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="text-lg">
          Multi-Agent Execution Progress: {progressPercentage}%
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <Progress value={progressPercentage} className="h-2" />

        {/* Empty State */}
        {agents.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No agents configured
          </div>
        )}

        {/* Agent List */}
        {agents.length > 0 && (
          <div className="space-y-4">
            {agents.map((agent, index) => (
              <div key={index}>
                <div className="flex items-center justify-between gap-4">
                  {/* Left: Icon + Name */}
                  <div className="flex items-center gap-3 flex-1">
                    <div
                      aria-label={`${agent.name} status: ${getStatusText(agent.status)}`}
                    >
                      {getStatusIcon(agent.status)}
                    </div>
                    <div>
                      <p className="font-medium">{agent.name}</p>
                    </div>
                  </div>

                  {/* Right: Status Badge */}
                  <Badge variant={getStatusVariant(agent.status)}>
                    {getStatusText(agent.status)}
                  </Badge>
                </div>

                {/* Connector Line (except for last item) */}
                {index < agents.length - 1 && (
                  <div className="ml-2.5 mt-2 mb-2 h-8 border-l-2 border-dashed border-gray-300" />
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
