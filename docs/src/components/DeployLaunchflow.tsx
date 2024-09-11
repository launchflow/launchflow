'use client'

import { Fence } from './Fence'
import { FrameImage } from './FrameImage'
import { useGettingStartedContext } from '@/components/GettingStartedSelector' // Import the context

export function DeployLaunchflow() {
  const ctx = useGettingStartedContext()

  return (
    <div>
      <Fence language="bash">lf init --backend=local</Fence>
      <p>
        Name your environment, select your cloud provider (
        <code>{ctx.selectedCloudProvider.name}</code>), confirm the resources to
        be created, and the service to deploy.
      </p>
      <hr />
      <p>
        Once complete you will see a link to your deployed service on{' '}
        {ctx.selectedRuntime.name}.
      </p>
      <FrameImage
        width={648}
        height={319}
        alt={`Deploy ${ctx.selectedRuntime.name}`}
        src={`/images/deploy-${ctx.selectedRuntime.name.replace(' ', '-').toLowerCase()}.png`}
      />
    </div>
  )
}
