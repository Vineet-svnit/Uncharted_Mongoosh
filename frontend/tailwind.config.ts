import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#0B1020",
          sidebar: "#10182A",
          surface: "#151F33",
          surfaceSecondary: "#1B2840",
          border: "#293750",
          hover: "#22314D",
        },
        accent: {
          primary: "#38BDF8", // Sky blue
          secondary: "#818CF8", // Indigo
          success: "#34D399", // Emerald
          warning: "#FBBF24", // Amber
          danger: "#FB7185", // Rose
        },
        slate: {
          text: "#F1F5F9",
          muted: "#94A3B8",
        },
      },
      fontFamily: {
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "Monaco", "Consolas", "monospace"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;

