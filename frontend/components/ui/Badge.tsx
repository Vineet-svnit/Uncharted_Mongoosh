import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "danger" | "info" | "outline";
  size?: "sm" | "md";
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  children,
  variant = "default",
  size = "sm",
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center font-medium rounded-full border transition-colors select-none";

  const variants = {
    default:
      "bg-dark-surfaceSecondary text-slate-muted border-dark-border",
    success:
      "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    warning:
      "bg-amber-500/15 text-amber-400 border-amber-500/30",
    danger:
      "bg-rose-500/15 text-rose-400 border-rose-500/30",
    info:
      "bg-sky-500/15 text-sky-400 border-sky-500/30",
    outline:
      "bg-transparent text-slate-muted border-dark-border",
  };

  const sizes = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-2.5 py-1 text-xs font-semibold gap-1.5",
  };

  return (
    <span
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </span>
  );
};

