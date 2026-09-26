/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0D6EFD", // Medical Blue
          hover: "#0256D0",
          light: "#EBF3FF",
        },
        secondary: {
          DEFAULT: "#0D9488", // Teal
          hover: "#0F766E",
          light: "#F0FDFA",
        },
        accent: {
          DEFAULT: "#10B981", // Emerald
          light: "#ECFDF5",
        },
        neutral: {
          dark: "#1F2937",
          light: "#F9FAFB",
          card: "#FFFFFF",
          border: "#E5E7EB",
        }
      },
      borderRadius: {
        "lg": "1rem",
        "xl": "1.5rem",
      },
      boxShadow: {
        "soft": "0 10px 30px -10px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02)",
        "premium": "0 20px 40px -15px rgba(13, 110, 253, 0.08), 0 1px 3px rgba(0, 0, 0, 0.01)",
      }
    },
  },
  plugins: [],
}
