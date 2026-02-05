"use client"

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { useTasks } from "@/lib/hooks/useTasks"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ListTodo,
  CheckCircle2,
  Calendar,
  TrendingUp,
  Clock
} from "lucide-react"
import { formatDistanceToNow } from "@/lib/utils"

export function StatsOverview() {
  const { data: tasks, isLoading } = useTasks()

  // Fetch success rate from API
  const { data: successRateData } = useQuery({
    queryKey: ['stats', 'success-rate', 7],
    queryFn: async () => {
      const res = await fetch('/api/stats/success-rate?days=7')
      if (!res.ok) throw new Error('Failed to fetch success rate')
      return res.json()
    },
    refetchInterval: 60000, // Refresh every minute
  })

  const stats = useMemo(() => {
    if (!tasks) {
      return {
        totalTasks: 0,
        activeTasks: 0,
        tasksRunToday: 0,
        successRate: 0,
        nextScheduledTask: null as { name: string; nextRun: string } | null,
      }
    }

    // Calculate active tasks
    const activeTasks = tasks.filter(task => task.enabled).length

    // Calculate tasks run today
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const tasksRunToday = tasks.filter(task => {
      if (!task.lastRun) return false
      const lastRunDate = new Date(task.lastRun)
      return lastRunDate >= today
    }).length

    // Get success rate from API (real data from TaskExecution table)
    const successRate = successRateData?.success_rate ?? 0

    // Find next scheduled task
    const enabledTasks = tasks.filter(task => task.enabled && task.nextRun)
    const nextScheduledTask = enabledTasks.length > 0
      ? enabledTasks.reduce((earliest, task) => {
          if (!earliest) return task
          return new Date(task.nextRun!) < new Date(earliest.nextRun!)
            ? task
            : earliest
        }, enabledTasks[0])
      : null

    return {
      totalTasks: tasks.length,
      activeTasks,
      tasksRunToday,
      successRate,
      nextScheduledTask: nextScheduledTask ? {
        name: nextScheduledTask.name,
        nextRun: nextScheduledTask.nextRun!,
      } : null,
    }
  }, [tasks])

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Total Tasks */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Tasks</CardTitle>
          <ListTodo className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.totalTasks}</div>
          <p className="text-xs text-muted-foreground">
            {stats.activeTasks} active
          </p>
        </CardContent>
      </Card>

      {/* Active Tasks */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Tasks</CardTitle>
          <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.activeTasks}</div>
          <p className="text-xs text-muted-foreground">
            {stats.totalTasks - stats.activeTasks} disabled
          </p>
        </CardContent>
      </Card>

      {/* Tasks Run Today */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Tasks Run Today</CardTitle>
          <Calendar className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.tasksRunToday}</div>
          <p className="text-xs text-muted-foreground">
            Last 24 hours
          </p>
        </CardContent>
      </Card>

      {/* Success Rate or Next Task */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            {stats.nextScheduledTask ? "Next Task" : "Success Rate"}
          </CardTitle>
          {stats.nextScheduledTask ? (
            <Clock className="h-4 w-4 text-muted-foreground" />
          ) : (
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          )}
        </CardHeader>
        <CardContent>
          {stats.nextScheduledTask ? (
            <>
              <div className="text-2xl font-bold truncate" title={stats.nextScheduledTask.name}>
                {stats.nextScheduledTask.name.length > 15
                  ? `${stats.nextScheduledTask.name.substring(0, 15)}...`
                  : stats.nextScheduledTask.name
                }
              </div>
              <p className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(stats.nextScheduledTask.nextRun))}
              </p>
            </>
          ) : (
            <>
              <div className="text-2xl font-bold">{stats.successRate}%</div>
              <p className="text-xs text-muted-foreground">
                Last 7 days
              </p>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
