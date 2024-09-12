import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/20/solid'

const styles = {
  note: {
    container:
      'border-blue-400 bg-blue-50 dark:bg-slate-800 dark:border-blue-900',
    icon: 'text-blue-400',
    body: 'text-blue-700 dark:text-blue-400',
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
      className={`callout border-l-4 p-4 callout-${type} ${style.container}`}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <IconComponent
            aria-hidden="true"
            className={`h-5 w-5 ${style.icon}`}
          />
        </div>
        <div className="ml-3">
          <span className={`${style.body}`}>
            <div className="-my-5">{children}</div>
          </span>
        </div>
      </div>
    </div>
  )
}
