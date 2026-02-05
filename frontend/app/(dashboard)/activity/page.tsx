"use client"

import { ActivityFeed } from "@/components/activity";

export default function ActivityPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Activity Log</h1>
        <p className="text-muted-foreground">
          System events and execution history
        </p>
      </div>

      <ActivityFeed />
    </div>
  );
}
