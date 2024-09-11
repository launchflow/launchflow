'use client'
import React from 'react'
import { useGettingStartedContext } from '@/components/GettingStartedSelector' // Import the context
import { Fence } from './Fence'
import Link from 'next/link'

type LFInitProps = {
  children: React.ReactNode
}

const cloudRunCode = `import launchflow as lf

# Cloud Run Docs: https://docs.launchflow.com/reference/gcp-services/cloud-run
service = lf.gcp.CloudRun(
    "my-cloud-run-service",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)`

const gceCode = `import launchflow as lf

# Compute Engine Docs: https://docs.launchflow.com/reference/gcp-services/compute-engine-service
service = lf.gcp.ComputeEngineService(
    "my-compute-engine-service",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
`

const gkeCode = `import launchflow as lf

# GKE Docs: https://docs.launchflow.com/reference/gcp-services/gke-service
cluster = lf.gcp.GKECluster("my-gke-cluster")
service = lf.gcp.GKEService(
    "my-gke-service",
    cluster=cluster,
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
`

const ecsFargateCode = `import launchflow as lf

# ECSFargate Docs: https://docs.launchflow.com/reference/aws-services/ecs-fargate
service = lf.aws.ECSFargate(
    "my-ecs-service",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
`

function CloudRunCodeBlock() {
  return (
    <div>
      <Fence language="python">{cloudRunCode}</Fence>
      <p>
        The service will build your Dockerfile and deploy to Cloud Run. You can{' '}
        <Link href="/reference/gcp-services/cloud-run">
          provide additional fields
        </Link>{' '}
        to <code>CloudRun</code> to configure things like CPU, num instances, or
        even a custom domain.
      </p>
    </div>
  )
}

function GCECodeBlock() {
  return (
    <div>
      <Fence language="python">{gceCode}</Fence>
      <p>
        The service will build your Dockerfile and deploy to Compute Engine. You
        can{' '}
        <Link href="/reference/gcp-services/compute-engine-service">
          provide additional fields
        </Link>{' '}
        to <code>ComputeEngineService</code> to configure things like machine
        type, num instances, or even a custom domain.
      </p>
    </div>
  )
}

function GKECodeBlock() {
  return (
    <div>
      <Fence language="python">{gkeCode}</Fence>
      <p>
        The service will build your Dockerfile and deploy to Kubernetes on GKE.
        You can{' '}
        <Link href="/reference/gcp-services/gke-service">
          provide additional fields
        </Link>{' '}
        to <code>GKEService</code> to configure things like startup propes, node
        pool, or even a custom domain.
      </p>
    </div>
  )
}

function ECSFargateCodeBlock() {
  return (
    <div>
      <Fence language="python">{ecsFargateCode}</Fence>
      <p>
        The service will build your Dockerfile and deploy to Compute Engine. You
        can{' '}
        <Link href="/reference/aws-services/ecs-fargate">
          provide additional fields
        </Link>{' '}
        to <code>ECSFargate</code> to configure things like machine type, num
        instances, or even a custom domain.
      </p>
    </div>
  )
}

export function LFInit({ children }: LFInitProps) {
  const ctx = useGettingStartedContext()

  let codeBlock = null
  if (ctx.selectedRuntime.name === 'Cloud Run') {
    codeBlock = <CloudRunCodeBlock />
  } else if (ctx.selectedRuntime.name === 'Compute Engine') {
    codeBlock = <GCECodeBlock />
  } else if (
    ctx.selectedRuntime.name === 'Kubernetes' &&
    ctx.selectedCloudProvider.name === 'GCP'
  ) {
    codeBlock = <GKECodeBlock />
  } else if (ctx.selectedRuntime.name === 'ECS Fargate') {
    codeBlock = <ECSFargateCodeBlock />
  }

  return (
    <div>
      <p>
        Install the LaunchFlow Python SDK and CLU using <code>pip</code>.
      </p>
      {ctx.selectedCloudProvider.name == 'GCP' ? (
        <Fence language="bash">pip install launchflow[gcp]</Fence>
      ) : (
        <Fence language="bash">pip install launchflow[aws]</Fence>
      )}
      <hr />
      <p>Initialize LaunchFlow in your project</p>
      <Fence language="bash">lf init --backend=local</Fence>
      <ul>
        <li>Name your project</li>
        <li>
          Select <code>Yes</code> for creating an example <code>infra.py</code>
        </li>
        <li>
          Select <code>{ctx.selectedCloudProvider.name}</code> for your cloud
          provider
        </li>
        <li>
          Select <code>{ctx.selectedRuntime.name}</code> for your service
        </li>
      </ul>
      {codeBlock && (
        <div>
          <p>
            Once finished you will get an <code>infra.py</code> that looks like:
          </p>
          {codeBlock}
        </div>
      )}
    </div>
  )
}
