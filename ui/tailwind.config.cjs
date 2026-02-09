/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#0a0d11',
          900: '#121826',
          800: '#182233',
          700: '#22304a',
          600: '#2f4060',
          500: '#3f5376'
        },
        mist: {
          300: '#9fb2d1',
          200: '#c7d2e6',
          100: '#eef2ff'
        },
        accent: {
          500: '#22d3ee',
          600: '#06b6d4'
        },
        accent2: {
          500: '#f97316',
          600: '#ea580c'
        },
        accent3: {
          500: '#a78bfa',
          600: '#8b5cf6'
        },
        warning: {
          500: '#f59e0b'
        },
        danger: {
          500: '#ef4444'
        }
      },
      fontFamily: {
        display: ['"Sora"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace']
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(94,234,212,0.2), 0 0 40px rgba(94,234,212,0.08)'
      }
    }
  },
  plugins: []
};
