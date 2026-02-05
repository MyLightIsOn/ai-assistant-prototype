import { TerminalView } from "@/components/terminal/TerminalView";

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
      </div>

      <TerminalView />
    </div>
  );
}
