'use client'
import { useGettingStartedContext } from '@/components/GettingStartedSelector' // Import the context
import Link from 'next/link'
import React from 'react'
import { Fence } from './Fence'

type LFInitProps = {
  children: React.ReactNode
}

const cloudRunCode = `import launchflow as lf

# Cloud Run Docs: https://docs.launchflow.com/reference/gcp-services/cloud-run
service = lf.gcp.CloudRunService(
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

# ECSFargateService Docs: https://docs.launchflow.com/reference/aws-services/ecs-fargate
api = lf.aws.ECSFargateService(
    "my-ecs-api",
    dockerfile="Dockerfile",  # Path to your Dockerfile
)
`

const lambdaCode = `import launchflow as lf

# LambdaService Docs: https://docs.launchflow.com/reference/aws-services/lambda-service
api = lf.aws.LambdaService("my-lambda-api", handler="TODO")
`

function CloudRunCodeBlock() {
  return (
    <div>
      <Fence language="python">{cloudRunCode}</Fence>
      <p>
        CloudRunService will build your Dockerfile and deploy to Cloud Run. You
        can{' '}
        <Link href="/reference/gcp-services/cloud-run">
          provide additional fields
        </Link>{' '}
        to <code>CloudRunService</code> to configure things like CPU, num
        instances, or even a custom domain.
      </p>
    </div>
  )
}

function GCECodeBlock() {
  return (
    <div>
      <Fence language="python">{gceCode}</Fence>
      <p>
        ComputeEngineService will build your Dockerfile and deploy to Compute
        Engine. You can{' '}
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
        GKEService will build your Dockerfile and deploy to Kubernetes on GKE.
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
        ECSFargateService will build your Dockerfile and deploy to ECS Fargate.
        You can{' '}
        <Link href="/reference/aws-services/ecs-fargate">
          provide additional fields
        </Link>{' '}
        to <code>ECSFargateService</code> to configure things like machine type,
        num instances, or even a custom domain.
      </p>
    </div>
  )
}

function LambdaCodeBlock() {
  return (
    <div>
      <Fence language="python">{lambdaCode}</Fence>
      <p>
        LambdaService will zip your local directory + Python environment and
        deploy it to AWS Lambda. You can{' '}
        <Link href="/reference/aws-services/lambda-service">
          provide additional fields
        </Link>{' '}
        to <code>LambdaService</code> to configure things like memory, timeout,
        or even a custom domain.
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
  } else if (ctx.selectedRuntime.name === 'Lambda') {
    codeBlock = <LambdaCodeBlock />
  }

  return (
    <div>
      <p>
        Install the LaunchFlow Python SDK and CLI using <code>pip</code>.
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
