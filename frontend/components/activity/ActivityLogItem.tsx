"use client"

import { ActivityLog } from "@/lib/types/api"
import { cn, formatDistanceToNow } from "@/lib/utils"
import {
  CheckCircle2,
  XCircle,
  Bell,
  PlayCircle,
  Info,
} from "lucide-react"
import Link from "next/link"

interface ActivityLogItemProps {
  log: ActivityLog
}

const logTypeConfig = {
  task_start: {
    icon: PlayCircle,
    iconClass: "text-blue-600 dark:text-blue-400",
    bgClass: "bg-blue-50 dark:bg-blue-950",
    dataIcon: "play",
  },
  task_complete: {
    icon: CheckCircle2,
    iconClass: "text-green-600 dark:text-green-400",
    bgClass: "bg-green-50 dark:bg-green-950",
    dataIcon: "check",
  },
  error: {
    icon: XCircle,
    iconClass: "text-red-600 dark:text-red-400",
    bgClass: "bg-red-50 dark:bg-red-950",
    dataIcon: "error",
  },
  notification_sent: {
    icon: Bell,
    iconClass: "text-purple-600 dark:text-purple-400",
    bgClass: "bg-purple-50 dark:bg-purple-950",
    dataIcon: "bell",
  },
  system: {
    icon: Info,
    iconClass: "text-gray-600 dark:text-gray-400",
    bgClass: "bg-gray-50 dark:bg-gray-950",
    dataIcon: "info",
  },
} as const

export function ActivityLogItem({ log }: ActivityLogItemProps) {
  const config =
    logTypeConfig[log.type as keyof typeof logTypeConfig] || logTypeConfig.system
  const Icon = config.icon

  // Parse metadata if available
  let metadata: Record<string, unknown> | null = null
  try {
    if (log.metadata) {
      metadata = JSON.parse(log.metadata)
    }
  } catch (error) {
    console.error("Failed to parse log metadata:", error)
  }

  // Format duration if available
  const duration = metadata?.duration
    ? typeof metadata.duration === "number"
      ? `${(metadata.duration / 1000).toFixed(2)}s`
      : metadata.duration
    : null

  // Extract status as string
  const status = metadata?.status && typeof metadata.status === "string" ? metadata.status : null

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border p-3 transition-colors hover:bg-accent/50",
        "sm:gap-4 sm:p-4"
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          config.bgClass
        )}
      >
        <Icon
          className={cn("h-4 w-4", config.iconClass)}
          data-icon={config.dataIcon}
        />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-1 overflow-hidden">
        {/* Message */}
        <p className="text-sm font-medium leading-tight line-clamp-2">
          {log.message}
        </p>

        {/* Metadata and timestamp */}
        <div className="flex flex-col gap-2 text-xs text-muted-foreground sm:flex-row sm:items-center sm:gap-4">
          <span>{formatDistanceToNow(new Date(log.createdAt))}</span>

          {log.executionId && (
            <Link
              href={`/executions/${log.executionId}`}
              className="hover:underline"
            >
              {log.executionId}
            </Link>
          )}

          {duration && (
            <span className="text-muted-foreground/70">
              Duration: {String(duration)}
            </span>
          )}

          {status && (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                status === "success"
                  ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                  : status === "error"
                  ? "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                  : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
              )}
            >
              {status}
            </span>
          )}
        </div>

        {/* Additional metadata */}
        {metadata && Object.keys(metadata).length > 2 && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:underline">
              View details
            </summary>
            <pre className="mt-2 overflow-x-auto rounded bg-muted p-2">
              {JSON.stringify(metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  )
}
