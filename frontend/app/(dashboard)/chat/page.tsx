import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MessageSquare, Send } from "lucide-react";

export default function ChatPage() {
  return (
    <div className="flex h-full flex-col space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Chat</h1>
        <p className="text-muted-foreground">
          Interact with your AI assistant
        </p>
      </div>

      <Card className="flex-1 flex flex-col">
        <CardHeader>
          <CardTitle>AI Assistant Chat</CardTitle>
          <CardDescription>
            Start a conversation with Claude
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col">
          <div className="flex-1 flex items-center justify-center text-center py-12">
            <div className="space-y-4">
              <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground" />
              <p className="text-muted-foreground">
                No messages yet. Start a conversation!
              </p>
            </div>
          </div>
          <div className="flex gap-2 pt-4 border-t">
            <Input
              placeholder="Type your message..."
              className="flex-1"
              disabled
            />
            <Button disabled>
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
