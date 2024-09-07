import Link from 'next/link'

const keywordColors = {
  python:
    'inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-600 ring-1 ring-inset ring-yellow-500/10',
  javascript:
    'inline-flex items-center rounded-md bg-orange-50 px-2 py-1 text-xs font-medium text-orange-600 ring-1 ring-inset ring-orange-500/10',
  api: 'inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-600 ring-1 ring-inset ring-blue-500/10',
  website:
    'inline-flex items-center rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-600 ring-1 ring-inset ring-red-500/10',
  worker:
    'inline-flex items-center rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-600 ring-1 ring-inset ring-violet-500/10',
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
}: {
  title: string
  href: string
  keywords?: string[]
}) {
  return (
    <Link href={href} className="no-decoration">
      <div className="bg-card text-card-foreground h-full rounded-lg border shadow-sm hover:shadow-md">
        <div className="flex flex-col space-y-1.5 p-6">
          <h3 className="mt-0 text-2xl font-semibold leading-none tracking-tight">
            {title}
          </h3>
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

export function GettingStartedSearch() {
  const cards = [
    {
      title: 'FastAPI',
      href: '/docs/get-started/fastapi',
      keywords: ['python', 'api'],
    },
    {
      title: 'Flask',
      href: '/docs/get-started/flask',
      keywords: ['python', 'api'],
    },
    {
      title: 'Django',
      href: '/docs/get-started/django',
      keywords: ['python', 'api'],
    },
    {
      title: 'Docker Image',
      href: '/docs/get-started/docker-image',
      keywords: ['api', 'website', 'worker'],
    },
    // {
    //   title: 'SvelteKit',
    //   href: '/docs/get-started/svelte',
    //   keywords: ['javascript', 'backend', 'frontend', 'full-stack'],
    // },
  ]
  return (
    <div>
      <span className="group flex h-auto w-full items-center justify-center sm:justify-start md:flex-none md:rounded-lg md:py-2.5 md:pl-4 md:pr-3.5 md:text-sm md:ring-1 md:ring-slate-200 md:hover:ring-slate-300 dark:md:bg-background_dark/75 dark:md:ring-inset dark:md:ring-white/5 dark:md:hover:bg-slate-700/40 dark:md:hover:ring-slate-500">
        <SearchIcon className="h-5 w-5 flex-none fill-slate-400 group-hover:fill-slate-500 md:group-hover:fill-slate-400 dark:fill-slate-500" />
        <input
          className="flex-auto appearance-none bg-transparent pl-2 text-slate-900 outline-none placeholder:text-slate-400 focus:w-full focus:flex-none sm:text-sm dark:text-white [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden [&::-webkit-search-results-button]:hidden [&::-webkit-search-results-decoration]:hidden"
          placeholder="Find a guide..."
        />
      </span>
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {cards.map((card) => (
          <FrameWorkCard key={card.title} {...card} />
        ))}
      </div>
    </div>
  )
}
