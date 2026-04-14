import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ygo: {
          gold: "#C9A84C",
          dark: "#0F0F1A",
          card: "#1A1A2E",
          border: "#2A2A4A",
        },
      },
    },
  },
  plugins: [],
};

export default config;
