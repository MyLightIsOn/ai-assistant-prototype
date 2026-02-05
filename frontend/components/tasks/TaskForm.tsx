"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from "react-hook-form"
import { Task, CreateTaskInput, UpdateTaskInput } from "@/lib/types/api"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScheduleInput } from "./ScheduleInput"
import { useCreateTask, useUpdateTask } from "@/lib/hooks/useTasks"
import { toast } from "sonner"
import { Loader2 } from "lucide-react"

interface TaskFormProps {
  task?: Task
  mode?: "create" | "edit"
}

export function TaskForm({ task, mode = "create" }: TaskFormProps) {
  const router = useRouter()
  const createTask = useCreateTask()
  const updateTask = useUpdateTask()
  const isEditMode = mode === "edit" && !!task

  const form = useForm<CreateTaskInput | UpdateTaskInput>({
    defaultValues: {
      name: task?.name || "",
      description: task?.description || "",
      command: task?.command || "",
      args: task?.args || "",
      schedule: task?.schedule || "0 9 * * *",
      enabled: task?.enabled ?? true,
      priority: task?.priority || "default",
      notifyOn: task?.notifyOn || "completion,error",
    },
  })

  const [isSubmitting, setIsSubmitting] = useState(false)

  const onSubmit = async (data: CreateTaskInput | UpdateTaskInput) => {
    setIsSubmitting(true)
    try {
      if (isEditMode) {
        await updateTask.mutateAsync({
          id: task.id,
          data: data as UpdateTaskInput,
        })
        toast.success("Task updated successfully")
        router.push(`/tasks/${task.id}`)
      } else {
        const newTask = await createTask.mutateAsync(data as CreateTaskInput)
        toast.success("Task created successfully")
        router.push(`/tasks/${newTask.id}`)
      }
    } catch (error) {
      toast.error(
        isEditMode ? "Failed to update task" : "Failed to create task"
      )
      console.error(error)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              rules={{ required: "Task name is required" }}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Task Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Daily backup, Weekly report"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    A descriptive name for your task
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="What does this task do?"
                      className="resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Additional details about this task
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Command Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="command"
              rules={{ required: "Command is required" }}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Command</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., claude, python, npm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The command to execute (e.g., claude for AI tasks)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="args"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Arguments (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="e.g., --project myproject run task"
                      className="resize-none font-mono text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Command arguments and flags
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            <FormField
              control={form.control}
              name="schedule"
              rules={{ required: "Schedule is required" }}
              render={({ field }) => (
                <FormItem>
                  <FormLabel>When should this task run?</FormLabel>
                  <FormControl>
                    <ScheduleInput
                      value={field.value || "0 9 * * *"}
                      onChange={field.onChange}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormField
              control={form.control}
              name="priority"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Priority</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="default">Default</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Task execution priority
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="notifyOn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notifications</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="When to notify" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="never">Never</SelectItem>
                      <SelectItem value="error">Only on errors</SelectItem>
                      <SelectItem value="completion">
                        On completion
                      </SelectItem>
                      <SelectItem value="completion,error">
                        On completion and errors
                      </SelectItem>
                      <SelectItem value="always">Always</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    When to send notifications
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="enabled"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Enable Task</FormLabel>
                    <FormDescription>
                      Task will run according to schedule when enabled
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />
          </CardContent>
        </Card>

        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.back()}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isEditMode ? "Update Task" : "Create Task"}
          </Button>
        </div>
      </form>
    </Form>
  )
}
