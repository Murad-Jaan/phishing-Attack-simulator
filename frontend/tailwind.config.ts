import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--bg)',
        foreground: 'var(--text)',
        border: 'var(--border)',
        input: 'var(--control-border)',
        control: 'var(--control-border)',
        ring: 'var(--primary)',
        surface: 'var(--surface)',
        'surface-muted': 'var(--surface-muted)',
        card: {
          DEFAULT: 'var(--surface)',
          foreground: 'var(--text)',
        },
        popover: {
          DEFAULT: 'var(--surface)',
          foreground: 'var(--text)',
        },
        primary: {
          DEFAULT: 'var(--primary)',
          hover: 'var(--primary-hover)',
          foreground: 'var(--on-primary)',
          tint: 'var(--primary-tint)',
          'tint-border': 'var(--primary-tint-border)',
        },
        secondary: {
          DEFAULT: 'var(--surface-muted)',
          foreground: 'var(--text)',
        },
        muted: {
          DEFAULT: 'var(--surface-muted)',
          foreground: 'var(--text-muted)',
        },
        strong: 'var(--text-strong-muted)',
        danger: {
          DEFAULT: 'var(--danger)',
          hover: 'var(--danger-hover)',
          foreground: 'var(--on-danger)',
          tint: 'var(--danger-tint)',
          'tint-border': 'var(--danger-tint-border)',
        },
        destructive: {
          DEFAULT: 'var(--danger)',
          foreground: 'var(--on-danger)',
        },
        success: {
          DEFAULT: 'var(--success)',
          tint: 'var(--success-tint)',
          'tint-border': 'var(--success-tint-border)',
        },
        warning: {
          DEFAULT: 'var(--warning)',
          tint: 'var(--warning-tint)',
          'tint-border': 'var(--warning-tint-border)',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
