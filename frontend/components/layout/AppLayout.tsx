"use client";

import React, { useState } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useThreads } from "@/hooks/useThreads";
import { Drawer } from "@/components/ui/Drawer";

interface AppLayoutProps {
  activeThreadId?: string | null;
  activeIncidentId?: string | null;
  isInspectorOpen: boolean;
  onToggleInspector: () => void;
  inspectorContent?: React.ReactNode;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  activeThreadId,
  activeIncidentId,
  isInspectorOpen,
  onToggleInspector,
  inspectorContent,
  children,
}) => {
  const {
    threads,
    loading: loadingThreads,
    error: threadsError,
    health,
    healthError,
    deleteThread,
  } = useThreads(activeThreadId || undefined);

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-dark-bg text-slate-text">
      {/* Desktop Sidebar */}
      <div className="hidden md:block h-full">
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          loading={loadingThreads}
          error={threadsError}
          health={health}
          healthError={healthError}
          onDeleteThread={deleteThread}
        />
      </div>

      {/* Mobile Sidebar in Drawer */}
      <Drawer
        isOpen={mobileSidebarOpen}
        onClose={() => setMobileSidebarOpen(false)}
        title="Investigations"
        width="md"
      >
        <div className="-m-6 h-[calc(100vh-60px)]">
          <Sidebar
            threads={threads}
            activeThreadId={activeThreadId}
            loading={loadingThreads}
            error={threadsError}
            health={health}
            healthError={healthError}
            onDeleteThread={deleteThread}
            onCloseMobile={() => setMobileSidebarOpen(false)}
          />
        </div>
      </Drawer>

      {/* Main Content Area (Header + Chat + Inspector) */}
      <div className="flex flex-1 flex-col h-full min-w-0 overflow-hidden">
        <Header
          onToggleSidebar={() => setMobileSidebarOpen(true)}
          isInspectorOpen={isInspectorOpen}
          onToggleInspector={onToggleInspector}
          health={health}
          healthError={healthError}
          activeIncidentId={activeIncidentId}
        />

        {/* Workspace Panels (Chat center + Inspector right) */}
        <div className="flex flex-1 h-[calc(100vh-3.5rem)] overflow-hidden">
          {/* Main Chat Center Panel */}
          <main className="flex-1 flex flex-col h-full min-w-0 bg-dark-bg overflow-hidden relative">
            {children}
          </main>

          {/* Desktop Right-side Investigation Inspector */}
          {isInspectorOpen && inspectorContent && (
            <aside className="hidden xl:flex w-[480px] 2xl:w-[540px] flex-col h-full border-l border-dark-border bg-dark-surface/95 shrink-0 overflow-hidden shadow-xl z-10 transition-all">
              {inspectorContent}
            </aside>
          )}

          {/* Mobile / Tablet Drawer for Inspector */}
          {isInspectorOpen && inspectorContent && (
            <div className="xl:hidden">
              <Drawer
                isOpen={isInspectorOpen}
                onClose={onToggleInspector}
                title="Investigation Inspector"
                width="xl"
              >
                <div className="-m-6 h-[calc(100vh-60px)]">{inspectorContent}</div>
              </Drawer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

