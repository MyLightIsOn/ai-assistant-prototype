"use client"

import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Mail } from "lucide-react"

interface DigestSettings {
  id: string
  dailyEnabled: boolean
  dailyTime: string
  weeklyEnabled: boolean
  weeklyDay: string
  weeklyTime: string
  recipientEmail: string
  createdAt: string
  updatedAt: string
}

export function DigestSettings() {
  const queryClient = useQueryClient()

  // Local state for form fields
  const [dailyEnabled, setDailyEnabled] = useState(true)
  const [dailyTime, setDailyTime] = useState("20:00")
  const [weeklyEnabled, setWeeklyEnabled] = useState(true)
  const [weeklyDay, setWeeklyDay] = useState("monday")
  const [weeklyTime, setWeeklyTime] = useState("09:00")
  const [recipientEmail, setRecipientEmail] = useState("")

  // Fetch digest settings
  const { data: settings, isLoading } = useQuery<DigestSettings>({
    queryKey: ["digest-settings"],
    queryFn: async () => {
      const res = await fetch("http://localhost:8000/api/settings/digest")
      if (!res.ok) {
        throw new Error("Failed to fetch digest settings")
      }
      return res.json()
    },
  })

  // Update local state when data is fetched
  useEffect(() => {
    if (settings) {
      // Use queueMicrotask to avoid cascading renders
      queueMicrotask(() => {
        setDailyEnabled(settings.dailyEnabled)
        setDailyTime(settings.dailyTime)
        setWeeklyEnabled(settings.weeklyEnabled)
        setWeeklyDay(settings.weeklyDay)
        setWeeklyTime(settings.weeklyTime)
        setRecipientEmail(settings.recipientEmail)
      })
    }
  }, [settings])

  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: async (updates: Partial<DigestSettings>) => {
      const res = await fetch("http://localhost:8000/api/settings/digest", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updates),
      })
      if (!res.ok) {
        throw new Error("Failed to update settings")
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["digest-settings"] })
      alert("Settings updated successfully!")
    },
    onError: (error) => {
      alert(`Failed to update settings: ${error.message}`)
    },
  })

  // Send test digest mutation
  const testMutation = useMutation({
    mutationFn: async (type: "daily" | "weekly") => {
      const res = await fetch(`http://localhost:8000/api/settings/digest/test?digest_type=${type}`, {
        method: "POST",
      })
      if (!res.ok) {
        throw new Error("Failed to send test digest")
      }
      return res.json()
    },
    onSuccess: (data, type) => {
      alert(`Test ${type} digest has been sent to ${recipientEmail}`)
    },
    onError: (error) => {
      alert(`Failed to send test digest: ${error.message}`)
    },
  })

  const handleSave = () => {
    updateMutation.mutate({
      dailyEnabled,
      dailyTime,
      weeklyEnabled,
      weeklyDay,
      weeklyTime,
      recipientEmail,
    })
  }

  const handleTestDaily = () => {
    testMutation.mutate("daily")
  }

  const handleTestWeekly = () => {
    testMutation.mutate("weekly")
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            <CardTitle>Email Digests</CardTitle>
          </div>
          <CardDescription>
            Configure automated daily and weekly summary emails
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading settings...</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          <CardTitle>Email Digests</CardTitle>
        </div>
        <CardDescription>
          Configure automated daily and weekly summary emails
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Daily Digest */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Daily Digest</Label>
              <p className="text-sm text-muted-foreground">
                Receive daily summary at a specific time
              </p>
            </div>
            <Switch
              checked={dailyEnabled}
              onCheckedChange={setDailyEnabled}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="daily-time">Daily Time</Label>
            <Input
              id="daily-time"
              type="time"
              value={dailyTime}
              onChange={(e) => setDailyTime(e.target.value)}
              disabled={!dailyEnabled}
            />
          </div>
        </div>

        {/* Weekly Digest */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Weekly Summary</Label>
              <p className="text-sm text-muted-foreground">
                Receive weekly summary on a specific day
              </p>
            </div>
            <Switch
              checked={weeklyEnabled}
              onCheckedChange={setWeeklyEnabled}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="weekly-day">Weekly Day</Label>
            <Select
              value={weeklyDay}
              onValueChange={setWeeklyDay}
              disabled={!weeklyEnabled}
            >
              <SelectTrigger id="weekly-day">
                <SelectValue placeholder="Select day" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="monday">Monday</SelectItem>
                <SelectItem value="tuesday">Tuesday</SelectItem>
                <SelectItem value="wednesday">Wednesday</SelectItem>
                <SelectItem value="thursday">Thursday</SelectItem>
                <SelectItem value="friday">Friday</SelectItem>
                <SelectItem value="saturday">Saturday</SelectItem>
                <SelectItem value="sunday">Sunday</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="weekly-time">Weekly Time</Label>
            <Input
              id="weekly-time"
              type="time"
              value={weeklyTime}
              onChange={(e) => setWeeklyTime(e.target.value)}
              disabled={!weeklyEnabled}
            />
          </div>
        </div>

        {/* Recipient Email */}
        <div className="grid gap-2">
          <Label htmlFor="recipient-email">Recipient Email</Label>
          <Input
            id="recipient-email"
            type="email"
            placeholder="you@example.com"
            value={recipientEmail}
            onChange={(e) => setRecipientEmail(e.target.value)}
          />
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending}
          >
            {updateMutation.isPending ? "Saving..." : "Save Settings"}
          </Button>
          <Button
            variant="outline"
            onClick={handleTestDaily}
            disabled={testMutation.isPending}
          >
            Send Test Daily Digest
          </Button>
          <Button
            variant="outline"
            onClick={handleTestWeekly}
            disabled={testMutation.isPending}
          >
            Send Test Weekly Summary
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
