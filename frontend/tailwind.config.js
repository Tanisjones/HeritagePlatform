/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Primary - Warm terracotta (heritage/earth tones)
        primary: {
          50: '#fdf4f1',
          100: '#fae7e0',
          200: '#f5cfc0',
          300: '#efb29b',
          400: '#e68d72',
          500: '#c76b4a',
          600: '#b55a3a',
          700: '#9a4a2f',
          800: '#7f3d28',
          900: '#663222',
        },
        // Secondary - Deep teal (knowledge/education)
        secondary: {
          50: '#f0f9f9',
          100: '#d9f0ed',
          200: '#b3e1db',
          300: '#80ccc3',
          400: '#52b3a8',
          500: '#2a9d8f',
          600: '#227f74',
          700: '#1f7268',
          800: '#1a5a52',
          900: '#164742',
        },
        // Neutral - Warm grays
        neutral: {
          50: '#fafaf9',
          100: '#f5f5f4',
          200: '#e7e5e4',
          300: '#d6d3d1',
          400: '#a8a29e',
          500: '#78716c',
          600: '#57534e',
          700: '#44403c',
          800: '#292524',
          900: '#1c1917',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Playfair Display', 'serif'],
      },
      fontSize: {
        xs: '0.75rem',
        sm: '0.875rem',
        base: '1rem',
        lg: '1.125rem',
        xl: '1.25rem',
        '2xl': '1.5rem',
        '3xl': '1.875rem',
        '4xl': '2.25rem',
      },
      screens: {
        'sm': '640px',   // Small tablets
        'md': '768px',   // Tablets
        'lg': '1024px',  // Desktop
        'xl': '1280px',  // Large desktop
      },
    },
  },
  plugins: [],
}
