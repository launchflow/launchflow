'use client'

import Image from 'next/image'
import Link from 'next/link'
import { useState } from 'react'

const keywordColors = {
  python:
    'inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-400/10 px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-500 ring-1 ring-inset ring-blue-500/10 dark:ring-blue-400/20',
  javascript:
    'inline-flex items-center rounded-md bg-yellow-50 dark:bg-yellow-400/10 px-2 py-1 text-xs font-medium text-yellow-600 dark:text-yellow-500 ring-1 ring-inset ring-yellow-500/10 dark:ring-yellow-400/20',
  rust: 'inline-flex items-center rounded-md bg-orange-50 dark:bg-orange-400/10 px-2 py-1 text-xs font-medium text-orange-600 dark:text-orange-500 ring-1 ring-inset ring-orange-500/10 dark:ring-orange-400/20',
  go: 'inline-flex items-center rounded-md bg-cyan-50 dark:bg-cyan-400/10 px-2 py-1 text-xs font-medium text-cyan-600 dark:text-cyan-500 ring-1 ring-inset ring-cyan-500/10 dark:ring-cyan-400/20',
  api: 'inline-flex items-center rounded-md bg-teal-50 dark:bg-teal-400/10 px-2 py-1 text-xs font-medium text-teal-600 dark:text-teal-500 ring-1 ring-inset ring-teal-500/10 dark:ring-teal-400/20',
  website:
    'inline-flex items-center rounded-md bg-green-50 dark:bg-green-400/10 px-2 py-1 text-xs font-medium text-green-600 dark:text-green-500 ring-1 ring-inset ring-red-500/10 dark:ring-green-400/20',
  worker:
    'inline-flex items-center rounded-md bg-violet-50 dark:bg-violet-400/10 px-2 py-1 text-xs font-medium text-violet-600 dark:text-violet-500 ring-1 ring-inset ring-violet-500/10 dark:ring-violet-400/20',
}

function SearchIcon(props: React.ComponentPropsWithoutRef<'svg'>) {
  return (
    <svg aria-hidden="true" viewBox="0 0 20 20" {...props}>
      <path d="M16.293 17.707a1 1 0 0 0 1.414-1.414l-1.414 1.414ZM9 14a5 5 0 0 1-5-5H2a7 7 0 0 0 7 7v-2ZM4 9a5 5 0 0 1 5-5V2a7 7 0 0 0-7 7h2Zm5-5a5 5 0 0 1 5 5h2a7 7 0 0 0-7-7v2Zm8.707 12.293-3.757-3.757-1.414 1.414 3.757 3.757 1.414-1.414ZM14 9a4.98 4.98 0 0 1-1.464 3.536l1.414 1.414A6.98 6.98 0 0 0 16 9h-2Zm-1.464 3.536A4.98 4.98 0 0 1 9 14v2a6.98 6.98 0 0 0 4.95-2.05l-1.414-1.414Z" />
    </svg>
  )
}

function FrameWorkCard({
  title,
  href,
  keywords,
  logo,
}: {
  title: string
  href: string
  keywords?: string[]
  logo?: string
  width?: number
  height?: number
}) {
  return (
    <Link href={href} className="no-decoration">
      <div className="bg-card text-card-foreground h-full rounded-lg border shadow-sm hover:shadow-md dark:border-white/5 dark:hover:shadow-slate-800">
        <div className="flex flex-col space-y-1.5 p-6">
          <div className="flex justify-between">
            <h3 className="mt-0 text-2xl font-semibold leading-none tracking-tight">
              {title}
            </h3>
            {logo && (
              <Image
                height={500}
                width={500}
                src={logo}
                alt={title}
                className="h-8 w-8"
              />
            )}
          </div>
          <div className="flex flex-wrap gap-1">
            {keywords?.map((keyword) => {
              const clz =
                keywordColors[keyword as keyof typeof keywordColors] ||
                'inline-flex items-center rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10'
              return (
                <span key={keyword} className={clz}>
                  {keyword}
                </span>
              )
            })}
          </div>
        </div>
      </div>
    </Link>
  )
}

const cards = [
  {
    title: 'Axum',
    href: '/docs/get-started/axum',
    keywords: ['rust', 'api'],
    logo: '/images/rustacean.svg',
  },
  {
    title: 'FastAPI',
    href: '/docs/get-started/fastapi',
    keywords: ['python', 'api'],
    logo: '/images/fastapi.png',
  },
  {
    title: 'Flask',
    href: '/docs/get-started/flask',
    keywords: ['python', 'api'],
    logo: '/images/flask.png',
  },
  {
    title: 'Django',
    href: '/docs/get-started/django',
    keywords: ['python', 'api'],
    logo: '/images/django.png',
  },
  {
    title: 'Go',
    href: '/docs/get-started/golang',
    keywords: ['go', 'api'],
    logo: '/images/golang.svg',
  },
  {
    title: 'Next.js',
    href: '/docs/get-started/next-js',
    keywords: ['javascript', 'api', 'website'],
    logo: '/images/next-js.png',
  },
  {
    title: 'Docker',
    href: '/docs/get-started/docker-image',
    keywords: ['api', 'website', 'worker'],
    logo: '/images/docker.png',
  },
]

export function GettingStartedSearch() {
  function searchGuides(query: string) {
    const q = query.toLowerCase()
    setVisibleCards(
      cards.filter((card) => {
        return (
          card.title.toLowerCase().includes(q) ||
          (card.keywords || []).some((k) => k.includes(q))
        )
      }),
    )
  }

  const [visibleCards, setVisibleCards] = useState(cards)
  return (
    <div>
      <span className="group flex h-auto w-full items-center justify-center sm:justify-start md:flex-none md:rounded-lg md:py-2.5 md:pl-4 md:pr-3.5 md:text-sm md:ring-1 md:ring-slate-200 md:hover:ring-slate-300 dark:md:bg-background_dark/75 dark:md:ring-inset dark:md:ring-white/5 dark:md:hover:bg-slate-700/40 dark:md:hover:ring-slate-500">
        <SearchIcon className="h-5 w-5 flex-none fill-slate-400 group-hover:fill-slate-500 md:group-hover:fill-slate-400 dark:fill-slate-500" />
        <input
          className="flex-auto appearance-none bg-transparent pl-2 text-slate-900 outline-none placeholder:text-slate-400 focus:w-full focus:flex-none sm:text-sm dark:text-white [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden [&::-webkit-search-results-button]:hidden [&::-webkit-search-results-decoration]:hidden"
          placeholder="Find a guide..."
          onChange={(e) => searchGuides(e.target.value)}
        />
      </span>
      {visibleCards.length > 0 ? (
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {visibleCards.map((card) => (
            <FrameWorkCard key={card.title} {...card} />
          ))}
        </div>
      ) : (
        <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
          Can't find the guide your looking for? Don't worry you can deploy
          application that can be run in a{' '}
          <Link href="/docs/get-started/docker-image">docker image</Link>.
        </div>
      )}
    </div>
  )
}
