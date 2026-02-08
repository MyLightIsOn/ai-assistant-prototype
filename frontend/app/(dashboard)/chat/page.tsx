import { ChatContainer } from '@/components/chat/ChatContainer';

export default function ChatPage() {
  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="border-b p-4">
        <h1 className="text-2xl font-bold">AI Assistant Chat</h1>
        <p className="text-sm text-muted-foreground">
          Interact with your AI assistant
        </p>
      </div>

      <ChatContainer />
    </div>
  );
}
