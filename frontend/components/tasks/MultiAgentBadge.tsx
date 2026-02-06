"use client"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { Users, GitMerge } from "lucide-react"

interface MultiAgentBadgeProps {
  agentCount: number
  hasSynthesis?: boolean
  className?: string
}

export function MultiAgentBadge({
  agentCount,
  hasSynthesis = false,
  className,
}: MultiAgentBadgeProps) {
  // Don't render if no agents
  if (agentCount === 0) {
    return null
  }

  return (
    <Badge
      variant="secondary"
      className={cn(
        "flex items-center gap-1 bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
        className
      )}
      data-testid="multi-agent-badge"
    >
      <Users className="h-3 w-3" />
      <span>
        {agentCount} {agentCount === 1 ? "Agent" : "Agents"}
      </span>
      {hasSynthesis && (
        <GitMerge className="h-3 w-3 ml-0.5" data-testid="synthesis-icon" />
      )}
    </Badge>
  )
}
