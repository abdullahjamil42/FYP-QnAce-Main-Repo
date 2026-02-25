import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './stories/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background)',
        foreground: 'var(--color-foreground)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          dark: 'var(--color-primary-dark)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          purple: 'var(--color-accent-purple)',
        },
        gradient: {
          purple: 'var(--color-gradient-purple)',
          blue: 'var(--color-gradient-blue)',
          teal: 'var(--color-gradient-teal)',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      spacing: {
        'baseline': '8px',
      },
      gridTemplateColumns: {
        '12': 'repeat(12, minmax(0, 1fr))',
      },
      animation: {
        'micro': '80ms ease-out',
        'reveal': '300ms ease-out',
      },
      transitionDuration: {
        'micro': '80ms',
        'micro-fast': '120ms',
        'micro-slow': '220ms',
        'reveal-fast': '300ms',
        'reveal': '400ms',
        'reveal-slow': '550ms',
      },
      boxShadow: {
        'glow': '0 0 20px var(--color-accent)',
        'glow-purple': '0 0 20px var(--color-accent-purple)',
        'inner-glow': 'inset 0 0 20px rgba(0, 217, 255, 0.1)',
      },
    },
  },
  plugins: [],
}
export default config

