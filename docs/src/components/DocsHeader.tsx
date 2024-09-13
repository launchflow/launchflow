'use client'

import { usePathname } from 'next/navigation'

import { homeNavigation } from '@/lib/navigation'

export function DocsHeader({
  title,
  subtitle,
}: {
  title?: string
  subtitle?: string
}) {
  let pathname = usePathname()
  let section = homeNavigation.find((section) =>
    section.links.find((link) => link.href === pathname),
  )

  if (!title && !section) {
    return null
  }

  return (
    <div id="docHeader">
      <header className="mb-9 space-y-1">
        <div className="pb-4">
          {section && (
            <p className="font-display text-sm font-medium text-primary">
              {section.title}
            </p>
          )}
          {title && (
            <h1 className="font-display text-3xl tracking-tight text-slate-900 dark:text-white">
              {title}
            </h1>
          )}
          {subtitle && (
            <p className="text-md pt-2 text-slate-500 dark:text-slate-400">
              {subtitle}
            </p>
          )}
        </div>
        <hr />
      </header>
    </div>
  )
}
