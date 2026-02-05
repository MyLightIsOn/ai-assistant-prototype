"use client"

import * as React from "react"
import cronstrue from "cronstrue"
import { CronExpressionParser } from "cron-parser"
import { InfoIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Card } from "@/components/ui/card"

interface ScheduleInputProps {
  value: string
  onChange: (value: string) => void
  className?: string
}

interface CronParts {
  minute: string
  hour: string
  dayOfMonth: string
  month: string
  dayOfWeek: string
}

const PRESET_SCHEDULES = {
  daily: {
    label: "Daily",
    description: "Every day at a specific time",
    cron: "0 9 * * *",
  },
  weekly: {
    label: "Weekly",
    description: "Once a week on a specific day",
    cron: "0 9 * * 1",
  },
  monthly: {
    label: "Monthly",
    description: "Once a month on a specific day",
    cron: "0 9 1 * *",
  },
  hourly: {
    label: "Hourly",
    description: "Every hour",
    cron: "0 * * * *",
  },
}

const HOURS = Array.from({ length: 24 }, (_, i) => ({
  value: i.toString(),
  label: i.toString().padStart(2, "0"),
}))

const MINUTES = Array.from({ length: 60 }, (_, i) => ({
  value: i.toString(),
  label: i.toString().padStart(2, "0"),
}))

const DAYS_OF_WEEK = [
  { value: "0", label: "Sunday" },
  { value: "1", label: "Monday" },
  { value: "2", label: "Tuesday" },
  { value: "3", label: "Wednesday" },
  { value: "4", label: "Thursday" },
  { value: "5", label: "Friday" },
  { value: "6", label: "Saturday" },
]

const DAYS_OF_MONTH = Array.from({ length: 31 }, (_, i) => ({
  value: (i + 1).toString(),
  label: (i + 1).toString(),
}))

const MONTHS = [
  { value: "1", label: "January" },
  { value: "2", label: "February" },
  { value: "3", label: "March" },
  { value: "4", label: "April" },
  { value: "5", label: "May" },
  { value: "6", label: "June" },
  { value: "7", label: "July" },
  { value: "8", label: "August" },
  { value: "9", label: "September" },
  { value: "10", label: "October" },
  { value: "11", label: "November" },
  { value: "12", label: "December" },
]

const EXAMPLES = [
  { cron: "0 9 * * *", description: "Every day at 9:00 AM" },
  { cron: "0 */6 * * *", description: "Every 6 hours" },
  { cron: "30 14 * * 1-5", description: "Weekdays at 2:30 PM" },
  { cron: "0 0 1 * *", description: "First day of every month at midnight" },
  { cron: "0 9 * * 1", description: "Every Monday at 9:00 AM" },
]

function parseCronExpression(cron: string): CronParts | null {
  try {
    const parts = cron.trim().split(/\s+/)
    if (parts.length !== 5) return null

    return {
      minute: parts[0],
      hour: parts[1],
      dayOfMonth: parts[2],
      month: parts[3],
      dayOfWeek: parts[4],
    }
  } catch {
    return null
  }
}

function validateCronExpression(cron: string): boolean {
  try {
    CronExpressionParser.parse(cron)
    return true
  } catch {
    return false
  }
}

function getNextExecutions(cron: string, count: number = 5): string[] {
  try {
    const interval = CronExpressionParser.parse(cron)
    const executions: string[] = []

    for (let i = 0; i < count; i++) {
      const next = interval.next()
      executions.push(next.toDate().toLocaleString())
    }

    return executions
  } catch {
    return []
  }
}

function getHumanReadable(cron: string): string {
  try {
    return cronstrue.toString(cron, {
      throwExceptionOnParseError: false,
      verbose: true,
    })
  } catch {
    return "Invalid cron expression"
  }
}

export function ScheduleInput({
  value,
  onChange,
  className,
}: ScheduleInputProps) {
  const [activeTab, setActiveTab] = React.useState<string>("preset")
  const [cronParts, setCronParts] = React.useState<CronParts>(() => {
    const parts = parseCronExpression(value)
    return parts || { minute: "0", hour: "9", dayOfMonth: "*", month: "*", dayOfWeek: "*" }
  })
  const [rawInput, setRawInput] = React.useState(value)
  const [selectedPreset, setSelectedPreset] = React.useState<string>("")

  const isValid = validateCronExpression(value)
  const nextExecutions = isValid ? getNextExecutions(value) : []
  const humanReadable = getHumanReadable(value)

  const handlePresetChange = (presetKey: string) => {
    setSelectedPreset(presetKey)
    const preset = PRESET_SCHEDULES[presetKey as keyof typeof PRESET_SCHEDULES]
    if (preset) {
      onChange(preset.cron)
      setRawInput(preset.cron)
      const parts = parseCronExpression(preset.cron)
      if (parts) setCronParts(parts)
    }
  }

  const handleBuilderChange = (field: keyof CronParts, value: string) => {
    const newParts = { ...cronParts, [field]: value }
    setCronParts(newParts)
    const newCron = `${newParts.minute} ${newParts.hour} ${newParts.dayOfMonth} ${newParts.month} ${newParts.dayOfWeek}`
    onChange(newCron)
    setRawInput(newCron)
    setSelectedPreset("")
  }

  const handleRawInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setRawInput(newValue)

    if (validateCronExpression(newValue)) {
      onChange(newValue)
      const parts = parseCronExpression(newValue)
      if (parts) setCronParts(parts)
      setSelectedPreset("")
    }
  }

  const handleRawInputBlur = () => {
    if (!validateCronExpression(rawInput)) {
      setRawInput(value)
    }
  }

  const handleExampleClick = (cron: string) => {
    onChange(cron)
    setRawInput(cron)
    const parts = parseCronExpression(cron)
    if (parts) setCronParts(parts)
    setSelectedPreset("")
    setActiveTab("custom")
  }

  return (
    <TooltipProvider>
      <div className={cn("space-y-4", className)}>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="preset">Presets</TabsTrigger>
            <TabsTrigger value="builder">Visual Builder</TabsTrigger>
            <TabsTrigger value="custom">Custom</TabsTrigger>
          </TabsList>

          <TabsContent value="preset" className="space-y-4">
            <div className="grid gap-3">
              {Object.entries(PRESET_SCHEDULES).map(([key, preset]) => (
                <Card
                  key={key}
                  className={cn(
                    "cursor-pointer p-4 transition-colors hover:bg-accent",
                    selectedPreset === key && "border-primary bg-accent"
                  )}
                  onClick={() => handlePresetChange(key)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      handlePresetChange(key)
                    }
                  }}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <h4 className="font-medium leading-none">{preset.label}</h4>
                      <p className="text-muted-foreground text-sm">
                        {preset.description}
                      </p>
                      <code className="text-xs">{preset.cron}</code>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="builder" className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="hour">Hour</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="text-muted-foreground size-4 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Hour of the day (0-23) or * for every hour</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Select
                  value={cronParts.hour === "*" ? "*" : cronParts.hour}
                  onValueChange={(val) => handleBuilderChange("hour", val)}
                >
                  <SelectTrigger id="hour">
                    <SelectValue placeholder="Select hour" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="*">Every hour</SelectItem>
                    {HOURS.map((hour) => (
                      <SelectItem key={hour.value} value={hour.value}>
                        {hour.label}:00
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="minute">Minute</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="text-muted-foreground size-4 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Minute of the hour (0-59) or * for every minute</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Select
                  value={cronParts.minute === "*" ? "*" : cronParts.minute}
                  onValueChange={(val) => handleBuilderChange("minute", val)}
                >
                  <SelectTrigger id="minute">
                    <SelectValue placeholder="Select minute" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="*">Every minute</SelectItem>
                    {MINUTES.filter((_, i) => i % 5 === 0).map((minute) => (
                      <SelectItem key={minute.value} value={minute.value}>
                        :{minute.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="dayOfWeek">Day of Week</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="text-muted-foreground size-4 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Day of the week (0-6, Sunday=0) or * for every day</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Select
                  value={cronParts.dayOfWeek}
                  onValueChange={(val) => handleBuilderChange("dayOfWeek", val)}
                >
                  <SelectTrigger id="dayOfWeek">
                    <SelectValue placeholder="Select day" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="*">Every day</SelectItem>
                    {DAYS_OF_WEEK.map((day) => (
                      <SelectItem key={day.value} value={day.value}>
                        {day.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="dayOfMonth">Day of Month</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="text-muted-foreground size-4 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Day of the month (1-31) or * for every day</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Select
                  value={cronParts.dayOfMonth}
                  onValueChange={(val) => handleBuilderChange("dayOfMonth", val)}
                >
                  <SelectTrigger id="dayOfMonth">
                    <SelectValue placeholder="Select day" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="*">Every day</SelectItem>
                    {DAYS_OF_MONTH.map((day) => (
                      <SelectItem key={day.value} value={day.value}>
                        {day.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Label htmlFor="month">Month</Label>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <InfoIcon className="text-muted-foreground size-4 cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent>
                      <p className="max-w-xs">Month of the year (1-12) or * for every month</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <Select
                  value={cronParts.month}
                  onValueChange={(val) => handleBuilderChange("month", val)}
                >
                  <SelectTrigger id="month">
                    <SelectValue placeholder="Select month" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="*">Every month</SelectItem>
                    {MONTHS.map((month) => (
                      <SelectItem key={month.value} value={month.value}>
                        {month.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="custom" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="rawCron">Cron Expression</Label>
              <Input
                id="rawCron"
                value={rawInput}
                onChange={handleRawInputChange}
                onBlur={handleRawInputBlur}
                placeholder="0 9 * * *"
                className={cn(!isValid && rawInput && "border-destructive")}
                aria-invalid={!isValid && !!rawInput}
              />
              {!isValid && rawInput && (
                <p className="text-destructive text-sm">Invalid cron expression</p>
              )}
              <p className="text-muted-foreground text-xs">
                Format: minute hour day month day-of-week
              </p>
            </div>

            <div className="space-y-2">
              <h4 className="text-sm font-medium">Examples</h4>
              <div className="space-y-2">
                {EXAMPLES.map((example, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => handleExampleClick(example.cron)}
                    className="hover:bg-accent block w-full rounded-md border p-3 text-left transition-colors"
                  >
                    <code className="text-primary text-sm">{example.cron}</code>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {example.description}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {isValid && (
          <Card className="space-y-3 p-4">
            <div>
              <h4 className="mb-1 text-sm font-medium">Schedule Preview</h4>
              <p className="text-sm">{humanReadable}</p>
            </div>

            {nextExecutions.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-medium">Next 5 Executions</h4>
                <ul className="text-muted-foreground space-y-1 text-sm">
                  {nextExecutions.map((execution, index) => (
                    <li key={index} className="flex items-center gap-2">
                      <span className="text-primary">{index + 1}.</span>
                      <span>{execution}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div>
              <h4 className="mb-1 text-sm font-medium">Cron Expression</h4>
              <code className="text-primary rounded bg-muted px-2 py-1 text-sm">
                {value}
              </code>
            </div>
          </Card>
        )}
      </div>
    </TooltipProvider>
  )
}
