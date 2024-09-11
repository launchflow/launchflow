import Image from 'next/image'
import { Callout } from './Callout'
import { Fence } from './Fence'

export function LFCloud() {
  return (
    <div>
      <Image
        alt="LaunchFlow Cloud Console"
        width="861"
        height="1503"
        src="/images/console.png"
      />
      <Callout type="warning" title="">
        LaunchFlow Cloud usage is optional and free for individuals.
      </Callout>
      <p>
        Using the local backend like we did above works fine for starting a
        project, but doesn't offer a way to share state between multiple users.
        LaunchFlow Cloud is a web-based service for managing, sharing, and
        automating your infrastructure. It's free small teams and provides a
        simple, secure way to collaborate with your team and automate your
        release pipelines.
      </p>
      <p>
        Sign up for LaunchFlow Cloud and connect your local environment by
        running:
      </p>
      <Fence language="bash">lf init --backend=lf</Fence>
      <p>
        This will create a project in your LaunchFlow Cloud account and migrate
        your local state to the LaunchFlow Cloud backend.
      </p>
    </div>
  )
}
