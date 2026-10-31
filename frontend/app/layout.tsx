import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AegisRCA | Agentic Root Cause Analysis Dashboard",
  description:
    "Autonomous Root Cause Analysis platform for investigating cloud infrastructure outages with live tool execution, dependency tracing, and evidence verification.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-dark-bg text-slate-text min-h-screen antialiased selection:bg-accent-primary/20 selection:text-sky-300">
        {children}
      </body>
    </html>
  );
}

