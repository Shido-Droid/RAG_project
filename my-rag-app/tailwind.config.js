/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.4s ease-out forwards',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-5px)' },
          '100%': { transform: 'translateY(0px)' },
        }
      },
      typography: (theme) => ({
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: theme('colors.slate.700'),
            lineHeight: '1.8',
            p: {
              marginTop: '1.25em',
              marginBottom: '1.25em',
            },
            li: {
              marginTop: '0.5em',
              marginBottom: '0.5em',
            },
            'ul > li': {
              paddingLeft: '0.375em',
            },
            'h1, h2, h3, h4': {
              color: theme('colors.slate.800'),
              fontWeight: '700',
              marginTop: '1.5em',
              marginBottom: '0.8em',
              lineHeight: '1.3',
            },
            pre: {
              backgroundColor: theme('colors.slate.900'),
              color: theme('colors.slate.100'),
              borderRadius: theme('borderRadius.lg'),
              padding: theme('spacing.5'),
              border: '1px solid ' + theme('colors.indigo.500') + '20',
            },
            code: {
              color: theme('colors.indigo.600'),
              backgroundColor: theme('colors.indigo.50'),
              borderRadius: theme('borderRadius.md'),
              padding: '0.2rem 0.4rem',
              fontWeight: '600',
              border: '1px solid ' + theme('colors.indigo.100'),
            },
            'code::before': {
              content: '""',
            },
            'code::after': {
              content: '""',
            },
          },
        },
        invert: {
          css: {
            color: theme('colors.slate.300'),
            'h1, h2, h3, h4': {
              color: theme('colors.slate.100'),
            },
            code: {
              color: theme('colors.indigo.300'),
              backgroundColor: theme('colors.indigo.900') + '40', // 40 hex is ~25% alpha
              border: '1px solid ' + theme('colors.indigo.800') + '60',
            },
            strong: {
              color: theme('colors.white'),
            },
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
