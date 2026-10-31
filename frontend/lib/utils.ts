import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString?: string | null): string {
  if (!dateString) return "N/A";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  } catch {
    return dateString;
  }
}

export function formatTime(dateString?: string | null): string {
  if (!dateString) return "";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }) + " UTC";
  } catch {
    return dateString;
  }
}

export function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return "Recently";
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  } catch {
    return "Recently";
  }
}

export interface ToolMetadata {
  label: string;
  category: "incident" | "topology" | "deployment" | "telemetry" | "discussions" | "sla" | "visual" | "knowledge";
  icon: string;
  description: string;
}

export const TOOL_MAPPING: Record<string, ToolMetadata> = {
  list_known_incidents: {
    label: "Finding relevant incidents",
    category: "incident",
    icon: "AlertOctagon",
    description: "Searching historical incident records and post-mortems",
  },
  get_incident_details: {
    label: "Reading incident details",
    category: "incident",
    icon: "FileText",
    description: "Extracting timeline, impact metrics, and context",
  },
  trace_service_dependencies: {
    label: "Tracing service dependencies",
    category: "topology",
    icon: "Network",
    description: "Analyzing upstream & downstream microservice topology",
  },
  find_recent_deployments: {
    label: "Investigating deployments",
    category: "deployment",
    icon: "GitCommit",
    description: "Correlating recent PRs, code diffs, and release manifests",
  },
  search_engineering_knowledge: {
    label: "Searching engineering knowledge",
    category: "knowledge",
    icon: "BookOpen",
    description: "Scanning runbooks, architecture diagrams, and wikis",
  },
  query_service_telemetry: {
    label: "Analysing telemetry",
    category: "telemetry",
    icon: "Activity",
    description: "Evaluating metrics, latency spikes, and error rates",
  },
  search_incident_messages: {
    label: "Reviewing team discussions",
    category: "discussions",
    icon: "MessageSquare",
    description: "Analyzing Slack war room conversations and on-call notes",
  },
  retrieve_customer_sla: {
    label: "Reviewing SLA contract",
    category: "sla",
    icon: "ShieldAlert",
    description: "Assessing downtime impact against Master Services Agreement",
  },
  search_visual_evidence: {
    label: "Examining visual evidence",
    category: "visual",
    icon: "Image",
    description: "Retrieving dashboard screenshots and Grafana panels",
  },
  // Generic or composite tool event fallbacks
  investigation_tools: {
    label: "Querying infrastructure data",
    category: "topology",
    icon: "Search",
    description: "Executing investigation query suite",
  },
};

export function getToolInfo(toolName: string): ToolMetadata {
  return (
    TOOL_MAPPING[toolName] || {
      label: toolName
        .split("_")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" "),
      category: "knowledge",
      icon: "Terminal",
      description: `Executing tool ${toolName}`,
    }
  );
}

export function getRootCauseColor(status?: string): {
  badge: string;
  border: string;
  bg: string;
  text: string;
} {
  switch (status?.toLowerCase()) {
    case "confirmed":
      return {
        badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/40",
        border: "border-emerald-500/50",
        bg: "bg-emerald-950/20",
        text: "text-emerald-400",
      };
    case "likely":
      return {
        badge: "bg-sky-500/20 text-sky-400 border-sky-500/40",
        border: "border-sky-500/50",
        bg: "bg-sky-950/20",
        text: "text-sky-400",
      };
    case "possible":
      return {
        badge: "bg-amber-500/20 text-amber-400 border-amber-500/40",
        border: "border-amber-500/50",
        bg: "bg-amber-950/20",
        text: "text-amber-400",
      };
    case "unknown":
    default:
      return {
        badge: "bg-slate-500/20 text-slate-400 border-slate-500/40",
        border: "border-slate-600",
        bg: "bg-slate-900/40",
        text: "text-slate-400",
      };
  }
}

