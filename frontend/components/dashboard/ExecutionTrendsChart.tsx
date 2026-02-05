"use client"

import { useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useWebSocket } from "@/lib/hooks/useWebSocket"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { AlertCircle } from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts"

interface TrendData {
  date: string
  successful: number
  failed: number
  total: number
}

export function ExecutionTrendsChart() {
  const queryClient = useQueryClient()
  const { subscribe, isConnected } = useWebSocket({ autoConnect: true })

  // Fetch trend data
  const { data, isLoading, error } = useQuery<TrendData[]>({
    queryKey: ["stats", "execution-trends", 7],
    queryFn: async () => {
      const res = await fetch("/api/stats/execution-trends?days=7")
      if (!res.ok) throw new Error("Failed to fetch trend data")
      return res.json()
    },
    refetchInterval: 60000, // Refresh every minute
  })

  // Real-time updates via WebSocket
  useEffect(() => {
    if (!isConnected) return

    const unsubscribe = subscribe("*", (message) => {
      if (
        message.type === "execution_complete" ||
        message.type === "execution_start"
      ) {
        queryClient.invalidateQueries({ queryKey: ["stats", "execution-trends"] })
      }
    })

    return unsubscribe
  }, [isConnected, subscribe, queryClient])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Execution Trends (Last 7 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Execution Trends (Last 7 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="text-sm font-medium text-destructive">
              Failed to load trend data
            </p>
            <p className="text-xs text-muted-foreground">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Format date for chart display (MM/DD)
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return `${date.getMonth() + 1}/${date.getDate()}`
  }

  // Check if there's any data to display
  const hasData = data && data.some(d => d.total > 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Execution Trends (Last 7 Days)</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasData ? (
          <div className="flex items-center justify-center py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No execution data available for the last 7 days
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                className="text-xs"
              />
              <YAxis className="text-xs" />
              <Tooltip
                labelFormatter={(date) => new Date(date).toLocaleDateString()}
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="successful"
                stroke="#22c55e"
                name="Successful"
                strokeWidth={2}
                dot={{ fill: '#22c55e' }}
              />
              <Line
                type="monotone"
                dataKey="failed"
                stroke="#ef4444"
                name="Failed"
                strokeWidth={2}
                dot={{ fill: '#ef4444' }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
