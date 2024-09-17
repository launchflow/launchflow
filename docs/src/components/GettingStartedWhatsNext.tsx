import Link from 'next/link'

export function WhatsNext() {
  return (
    <ul>
      <li>
        <Link href="/docs/user-guides/add-resources">Add resources</Link> to
        your application
      </li>
      <li>
        <Link href="/docs/user-guides/promote-deployment">
          Promote your application
        </Link>{' '}
        to a production enviroment
      </li>
      <li>
        Learn more about{' '}
        <Link href="/docs/concepts/environments">Environments</Link>,{' '}
        <Link href="/docs/concepts/services">Services</Link>, and{' '}
        <Link href="/docs/concepts/resources">Resources</Link>
      </li>
      <li>
        Join the
        <Link href="/docs/user-guides/monitor-deployment">
          LaunchFlow Slack community
        </Link>
      </li>
      <li>
        View your application in the
        <Link href="https://console.launchflow.com">LaunchFlow console</Link>
      </li>
    </ul>
  )
}
