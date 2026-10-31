"use client";

import React, { useState, useEffect, useRef } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { useThreads } from "@/hooks/useThreads";
import { Drawer } from "@/components/ui/Drawer";
import { GripVertical } from "lucide-react";

interface AppLayoutProps {
  activeThreadId?: string | null;
  activeIncidentId?: string | null;
  isInspectorOpen: boolean;
  onToggleInspector: () => void;
  inspectorContent?: React.ReactNode;
  children: React.ReactNode;
}

const DEFAULT_INSPECTOR_WIDTH = 520;
const MIN_INSPECTOR_WIDTH = 380;
const MAX_INSPECTOR_WIDTH = 960;

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
  const [inspectorWidth, setInspectorWidth] = useState<number>(DEFAULT_INSPECTOR_WIDTH);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragRef = useRef<boolean>(false);

  // Load saved width on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("aegis_inspector_width");
      if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed >= MIN_INSPECTOR_WIDTH && parsed <= MAX_INSPECTOR_WIDTH) {
          setInspectorWidth(parsed);
        }
      }
    }
  }, []);

  const handleWidthChange = (newWidth: number) => {
    const clamped = Math.max(
      MIN_INSPECTOR_WIDTH,
      Math.min(newWidth, Math.min(MAX_INSPECTOR_WIDTH, window.innerWidth - 420))
    );
    setInspectorWidth(clamped);
    if (typeof window !== "undefined") {
      localStorage.setItem("aegis_inspector_width", String(clamped));
    }
  };

  // Drag-to-resize listener
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragRef.current = true;
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const newWidth = window.innerWidth - e.clientX;
      const maxAllowed = Math.min(MAX_INSPECTOR_WIDTH, window.innerWidth - 420);
      const clamped = Math.max(MIN_INSPECTOR_WIDTH, Math.min(newWidth, maxAllowed));
      setInspectorWidth(clamped);
    };

    const handleMouseUp = () => {
      if (dragRef.current) {
        dragRef.current = false;
        setIsDragging(false);
        setInspectorWidth((curr) => {
          if (typeof window !== "undefined") {
            localStorage.setItem("aegis_inspector_width", String(curr));
          }
          return curr;
        });
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  // Pass inspectorWidth and handleWidthChange to inspectorContent
  const enhancedInspectorContent =
    React.isValidElement(inspectorContent)
      ? React.cloneElement(inspectorContent as React.ReactElement<any>, {
          inspectorWidth,
          onWidthChange: handleWidthChange,
        })
      : inspectorContent;

  return (
    <div
      className={`flex h-screen w-screen overflow-hidden bg-dark-bg text-slate-text ${
        isDragging ? "select-none cursor-col-resize" : ""
      }`}
    >
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
        <div className="flex flex-1 h-[calc(100vh-3.5rem)] overflow-hidden relative">
          {/* Main Chat Center Panel */}
          <main className="flex-1 flex flex-col h-full min-w-0 bg-dark-bg overflow-hidden relative">
            {children}
          </main>

          {/* Desktop Right-side Investigation Inspector with Resizer */}
          {isInspectorOpen && enhancedInspectorContent && (
            <>
              {/* Draggable Divider Handle */}
              <div
                onMouseDown={handleMouseDown}
                className={`hidden lg:flex w-2 cursor-col-resize z-20 group relative items-center justify-center shrink-0 transition-colors ${
                  isDragging
                    ? "bg-accent-primary/50"
                    : "hover:bg-accent-primary/20 bg-dark-border/40"
                }`}
                title="Drag to resize inspector sidebar"
              >
                <div
                  className={`w-0.5 h-12 rounded-full transition-colors ${
                    isDragging
                      ? "bg-accent-primary shadow-[0_0_8px_rgba(56,189,248,0.8)]"
                      : "bg-dark-border group-hover:bg-accent-primary"
                  }`}
                />
              </div>

              {/* Inspector Panel */}
              <aside
                style={{ width: `${inspectorWidth}px` }}
                className="hidden lg:flex flex-col h-full border-l border-dark-border bg-dark-surface/95 shrink-0 overflow-hidden shadow-2xl z-10 transition-[width] duration-75"
              >
                {enhancedInspectorContent}
              </aside>
            </>
          )}

          {/* Mobile / Tablet Drawer for Inspector */}
          {isInspectorOpen && enhancedInspectorContent && (
            <div className="lg:hidden">
              <Drawer
                isOpen={isInspectorOpen}
                onClose={onToggleInspector}
                title="Investigation Inspector"
                width="xl"
              >
                <div className="-m-6 h-[calc(100vh-60px)]">{enhancedInspectorContent}</div>
              </Drawer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
