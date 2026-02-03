import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Terminal as TerminalIcon } from "lucide-react";

export default function TerminalPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Terminal</h1>
          <p className="text-muted-foreground">
            Real-time output from AI task execution
          </p>
        </div>
        <Badge variant="secondary">Idle</Badge>
      </div>

      <Card className="h-[600px] flex flex-col">
        <CardHeader>
          <CardTitle>Live Terminal Output</CardTitle>
          <CardDescription>
            Streaming output from Claude Code subprocess
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col">
          <div className="flex-1 bg-black/95 rounded-lg p-4 font-mono text-sm overflow-auto">
            <div className="flex items-center gap-2 text-green-400">
              <TerminalIcon className="h-4 w-4" />
              <span>Terminal ready. Waiting for task execution...</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
