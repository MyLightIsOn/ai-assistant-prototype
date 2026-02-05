import { StatsOverview } from "@/components/dashboard/StatsOverview"
import { RecentActivity } from "@/components/dashboard/RecentActivity"
import { UpcomingTasks } from "@/components/dashboard/UpcomingTasks"
import { QuickActions } from "@/components/dashboard/QuickActions"
import { ExecutionTrendsChart } from "@/components/dashboard/ExecutionTrendsChart"

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your AI assistant activity
        </p>
      </div>

      {/* Stats Overview */}
      <StatsOverview />

      {/* Activity and Upcoming Tasks Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        <RecentActivity />
        <UpcomingTasks />
      </div>

      {/* Quick Actions */}
      <QuickActions />

      {/* Execution Trends Chart */}
      <ExecutionTrendsChart />
    </div>
  )
}
