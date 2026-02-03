"use client";

import { SessionProvider } from "next-auth/react";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { Header } from "@/components/dashboard/Header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <SessionProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Sidebar - hidden on mobile, visible on desktop */}
        <aside className="hidden lg:block">
          <Sidebar />
        </aside>

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto p-6">
            {children}
          </main>
        </div>
      </div>
    </SessionProvider>
  );
}
