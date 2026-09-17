/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#12151C",
        panel: "#1B202B",
        panel2: "#212836",
        line: "#2A3140",
        ink: "#E8EAED",
        muted: "#8B93A1",
        faint: "#5B6373",
        accent: "#F2B705",
        accentDim: "#7A6112",
        good: "#3FB68B",
        bad: "#E2574C",
        info: "#4C8DFF",
        warn: "#E0A339",
      },
      fontFamily: {
        head: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains)", "monospace"],
      },
      borderRadius: {
        sm: "3px",
        DEFAULT: "5px",
        md: "6px",
        lg: "8px",
      },
    },
  },
  plugins: [],
};
