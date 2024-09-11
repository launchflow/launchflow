import clsx from 'clsx'

import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/20/solid'

const styles = {
  note: {
    container: 'border-blue-400 bg-blue-50',
    icon: 'text-blue-400',
    body: 'text-blue-700',
  },
  warning: {
    container: 'border-yellow-400 bg-yellow-50',
    icon: 'text-yellow-400',
    body: 'text-yellow-700',
  },
}

const icons = {
  note: (props: { className?: string }) => <InformationCircleIcon {...props} />,
  warning: (props: { className?: string }) => (
    <ExclamationTriangleIcon color="amber" {...props} />
  ),
}

export function CalloutOld({
  title,
  children,
  type = 'note',
}: {
  title: string
  children: React.ReactNode
  type?: keyof typeof styles
}) {
  let IconComponent = icons[type]

  return (
    <div
      className={clsx(
        'not-prose my-8 flex rounded-3xl p-6',
        styles[type].container,
      )}
    >
      <IconComponent className="h-8 w-8 flex-none" />
      <div className="ml-4 flex-auto">
        <p className={clsx('m-0 font-display text-xl', styles[type].title)}>
          {title}
        </p>
        <div className={clsx('prose mt-2.5', styles[type].body)}>
          {children}
        </div>
      </div>
    </div>
  )
}

export function Callout({
  children,
  type = 'note',
}: {
  children: React.ReactNode
  type?: keyof typeof styles
}) {
  let IconComponent = icons[type]
  let style = styles[type]

  return (
    <div
      className={`not-prose callout border-l-4 p-4 callout-${type}, ${style.container}`}
    >
      <div className="flex">
        <div className="flex items-center justify-center">
          <IconComponent
            aria-hidden="true"
            className={`h-5 w-5 ${style.icon}`}
          />
        </div>
        <div className="ml-3">
          <p className={`text-base ${style.body}`}>{children}</p>
        </div>
      </div>
    </div>
  )
}
