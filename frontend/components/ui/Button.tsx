import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "danger" | "ghost";
  size?: "sm" | "md" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      children,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none select-none";

    const variants = {
      primary:
        "bg-accent-primary text-slate-900 font-semibold hover:bg-sky-400 focus:ring-sky-400 focus:ring-offset-dark-bg shadow-sm shadow-sky-500/20 active:translate-y-0.5",
      secondary:
        "bg-dark-surfaceSecondary text-slate-text border border-dark-border hover:bg-dark-hover hover:border-slate-600 focus:ring-indigo-400 focus:ring-offset-dark-bg active:translate-y-0.5",
      outline:
        "bg-transparent text-slate-text border border-dark-border hover:bg-dark-surfaceSecondary hover:border-slate-500 focus:ring-sky-400 focus:ring-offset-dark-bg",
      danger:
        "bg-accent-danger/20 text-accent-danger border border-accent-danger/30 hover:bg-accent-danger/30 focus:ring-rose-400 focus:ring-offset-dark-bg",
      ghost:
        "bg-transparent text-slate-muted hover:text-slate-text hover:bg-dark-surfaceSecondary focus:ring-slate-500",
    };

    const sizes = {
      sm: "h-8 px-3 text-xs rounded-md gap-1.5",
      md: "h-9 px-4 text-sm rounded-lg gap-2",
      lg: "h-11 px-6 text-base rounded-lg gap-2.5",
      icon: "h-8 w-8 p-0 rounded-md",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-0.5 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";

