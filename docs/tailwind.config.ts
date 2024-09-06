import typographyPlugin from '@tailwindcss/typography'
import { type Config } from 'tailwindcss'

export default {
  content: ['./src/**/*.{js,jsx,ts,tsx,md}'],
  darkMode: ['selector', 'class'],
  theme: {
  	fontSize: {
  		xs: ['0.75rem', { lineHeight: '1rem' }],
  		sm: ['0.875rem', { lineHeight: '1.5rem' }],
  		base: ['1rem', { lineHeight: '2rem' }],
  		lg: ['1.125rem', { lineHeight: '1.75rem' }],
  		xl: ['1.25rem', { lineHeight: '2rem' }],
  		'2xl': ['1.5rem', { lineHeight: '2.5rem' }],
  		'3xl': ['2rem', { lineHeight: '2.5rem' }],
  		'4xl': ['2.5rem', { lineHeight: '3rem' }],
  		'5xl': ['3rem', { lineHeight: '3.5rem' }],
  		'6xl': ['3.75rem', { lineHeight: '1' }],
  		'7xl': ['4.5rem', { lineHeight: '1' }],
  		'8xl': ['6rem', { lineHeight: '1' }],
  		'9xl': ['8rem', { lineHeight: '1' }]
  	},
  	extend: {
  		fontFamily: {
  			sans: 'var(--font-inter)',
  			display: ['var(--font-lexend)', { fontFeatureSettings: 'ss01"' }]
  		},
  		maxWidth: {
  			'8xl': '88rem'
  		},
  		colors: {
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			logo: 'rgb(var(--color-logo) / <alpha-value>)',
  			background_dark: 'rgb(var(--color-background-dark) / <alpha-value>)',
  			background_light: 'rgb(var(--color-background-light) / <alpha-value>)',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  plugins: [typographyPlugin, require("tailwindcss-animate")],
} satisfies Config
