"use client"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  CheckCircle2,
  XCircle,
  Clock,
  PlayCircle,
  PauseCircle
} from "lucide-react"

interface TaskStatusBadgeProps {
  status: 'idle' | 'running' | 'success' | 'error' | 'pending'
  className?: string
  showIcon?: boolean
}

const statusConfig = {
  idle: {
    label: 'Idle',
    variant: 'secondary' as const,
    icon: PauseCircle,
    className: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
  },
  running: {
    label: 'Running',
    variant: 'default' as const,
    icon: PlayCircle,
    className: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
  },
  success: {
    label: 'Success',
    variant: 'secondary' as const,
    icon: CheckCircle2,
    className: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
  },
  error: {
    label: 'Error',
    variant: 'destructive' as const,
    icon: XCircle,
    className: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
  },
  pending: {
    label: 'Pending',
    variant: 'outline' as const,
    icon: Clock,
    className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300'
  }
}

export function TaskStatusBadge({
  status,
  className,
  showIcon = true
}: TaskStatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.idle
  const Icon = config.icon

  return (
    <Badge
      variant={config.variant}
      className={cn(config.className, className)}
    >
      {showIcon && <Icon className="h-3 w-3" />}
      {config.label}
    </Badge>
  )
}
