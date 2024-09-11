'use client'

import Link from 'next/link'
import { Fence } from './Fence'
import { FrameImage } from './FrameImage'
import { useGettingStartedContext } from '@/components/GettingStartedSelector' // Import the context

export function DeployLaunchflow() {
  const ctx = useGettingStartedContext()

  let credsHelpUrl = ''
  if (ctx.selectedCloudProvider.name == 'AWS') {
    credsHelpUrl = '/docs/user-guides/aws-authentication'
  } else if (ctx.selectedCloudProvider.name == 'GCP') {
    credsHelpUrl = '/docs/user-guides/gcp-authentication'
  }

  return (
    <div>
      <p>
        Before running the below command ensure that you have your{' '}
        {ctx.selectedCloudProvider.name == 'aws' ? 'AWS' : 'GCP'}{' '}
        <Link href={credsHelpUrl}>
          credentials set up on your local machine.
        </Link>
      </p>
      <Fence language="bash">lf deploy</Fence>
      <ul>
        <li>
          Name your environment (<code>dev</code> is a good first name)
        </li>
        <li>
          Select your cloud provider{' '}
          <code>{ctx.selectedCloudProvider.name}</code>)
        </li>
        <li>Confirm the resources to be created</li>
        <li>Select the service to deploy</li>
      </ul>
      <hr />
      <p>
        Once complete you will see a link to your deployed service on{' '}
        {ctx.selectedRuntime.name}.
      </p>
      <FrameImage
        width={648}
        alt={`Deploy ${ctx.selectedRuntime.name}`}
        src={`/images/deploy-${ctx.selectedCloudProvider.name.toLowerCase()}-${ctx.selectedRuntime.name.replace(' ', '-').toLowerCase()}.png`}
      />
    </div>
  )
}
