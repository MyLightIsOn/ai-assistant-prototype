"use client"

import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, ListTodo, Terminal, Activity } from "lucide-react"

export function QuickActions() {
  const router = useRouter()

  const actions = [
    {
      title: "Create Task",
      description: "Schedule a new automated task",
      icon: Plus,
      onClick: () => router.push("/tasks/new"),
      variant: "default" as const,
    },
    {
      title: "View Tasks",
      description: "Manage all scheduled tasks",
      icon: ListTodo,
      onClick: () => router.push("/tasks"),
      variant: "outline" as const,
    },
    {
      title: "Terminal",
      description: "View live task execution",
      icon: Terminal,
      onClick: () => router.push("/terminal"),
      variant: "outline" as const,
    },
    {
      title: "Activity Log",
      description: "Review system activity",
      icon: Activity,
      onClick: () => router.push("/activity"),
      variant: "outline" as const,
    },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
        <CardDescription>
          Common tasks and navigation shortcuts
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {actions.map((action) => {
            const Icon = action.icon
            return (
              <Button
                key={action.title}
                variant={action.variant}
                onClick={action.onClick}
                className="h-auto flex-col items-start gap-2 p-4 text-left"
              >
                <Icon className="h-5 w-5" />
                <div>
                  <div className="font-semibold">{action.title}</div>
                  <div className="text-xs font-normal text-muted-foreground">
                    {action.description}
                  </div>
                </div>
              </Button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
