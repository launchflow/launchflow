import clsx from 'clsx'
import Link from 'next/link'

const variantStyles = {
  primary:
    'rounded-full bg-primary py-2 px-4 text-sm font-semibold text-white hover:bg-[var(--color-primary-transition)] focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300/50 active:bg-sky-500',
  'primary-lg':
    'rounded-full bg-primary py-2 px-4 text-lg font-semibold text-white hover:bg-[var(--color-primary-transition)] focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-300/50 active:bg-sky-500',

  secondary:
    'rounded-full bg-secondary py-2 px-4 text-sm font-medium text-white hover:bg-slate-700 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/50 active:text-slate-400',
}

type ButtonProps = {
  variant?: keyof typeof variantStyles
} & (
  | React.ComponentPropsWithoutRef<typeof Link>
  | (React.ComponentPropsWithoutRef<'button'> & { href?: undefined })
)

export function Button({
  variant = 'primary',
  className,
  ...props
}: ButtonProps) {
  className = clsx(variantStyles[variant], className)

  return typeof props.href === 'undefined' ? (
    <button className={className} {...props} />
  ) : (
    <Link className={className} {...props} />
  )
}
