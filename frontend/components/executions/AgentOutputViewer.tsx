'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface AgentOutput {
  agentName: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  structuredOutput?: Record<string, any>
  narrativeOutput?: string
}

export interface AgentOutputViewerProps {
  agents: AgentOutput[]
  className?: string
}

const STATUS_VARIANTS = {
  completed: 'default' as const,
  running: 'secondary' as const,
  pending: 'outline' as const,
  failed: 'destructive' as const,
}

const STATUS_LABELS = {
  completed: 'Completed',
  running: 'Running',
  pending: 'Pending',
  failed: 'Failed',
}

export function AgentOutputViewer({ agents, className }: AgentOutputViewerProps) {
  const [activeTab, setActiveTab] = useState<string>(agents[0]?.agentName || '')

  if (agents.length === 0) {
    return (
      <Card className={cn('p-6', className)}>
        <div className="text-center text-muted-foreground">
          No agents to display
        </div>
      </Card>
    )
  }

  return (
    <div className={className}>
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full justify-start">
          {agents.map((agent) => (
            <TabsTrigger
              key={agent.agentName}
              value={agent.agentName}
              className="gap-2"
            >
              {agent.agentName}
              <Badge variant={STATUS_VARIANTS[agent.status]}>
                {STATUS_LABELS[agent.status]}
              </Badge>
            </TabsTrigger>
          ))}
        </TabsList>

        {agents.map((agent) => (
          <TabsContent key={agent.agentName} value={agent.agentName}>
            <Card>
              <CardContent className="space-y-6 pt-6">
                {!agent.structuredOutput && !agent.narrativeOutput && (
                  <div className="text-center text-muted-foreground py-8">
                    No outputs available yet. This agent has not produced any results.
                  </div>
                )}

                {agent.structuredOutput && (
                  <div>
                    <h3 className="text-sm font-semibold mb-3">
                      Structured Output (output.json):
                    </h3>
                    <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                      <code>{JSON.stringify(agent.structuredOutput, null, 2)}</code>
                    </pre>
                  </div>
                )}

                {agent.narrativeOutput && (
                  <div>
                    <h3 className="text-sm font-semibold mb-3">
                      Narrative Output (output.md):
                    </h3>
                    <div className="bg-muted rounded-lg p-4 overflow-x-auto">
                      <pre className="text-sm whitespace-pre-wrap">
                        {agent.narrativeOutput}
                      </pre>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
