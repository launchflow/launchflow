---
title: Deployments
nextjs:
  metadata:
    title: Deployments
    description: LaunchFlow Deployments
---


{% mdimage src="/images/services_light.svg" alt="diagram" className="block dark:hidden" height=250 width=600 /%}
{% mdimage src="/images/services_dark.svg" alt="diagram" className="hidden dark:block" height=250 width=600 /%}


## Overview

Deployments allow you to deploy websites, APIs, background workers and other types of applications to your cloud account with minimal setup. There are 3 deployment types: **Services**, **Workers**, and **Jobs**.

{% callout type="note" %}
**LaunchFlow is not just for deploying Python apps.**

The Python SDK is used to define your infrastructure in code, but you can deploy any static or Dockerized application to AWS or GCP.

Python is just the language for your DevOps automation.

{% /callout %}

### Services
Services are long-running applications that serve HTTP requests.

For example, you might create an Service to expose your API:

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f"Hello from {lf.environment}"

api = lf.gcp.CloudRun("my-service", region="us-central1")
```

Or you might use a Service to host your React app:

```python
import launchflow as lf

app = lf.gcp.CloudRun("my-web-app", build_directory="./react-app")
```

### Workers
Workers are long-running applications that process tasks and events.

For example, you might create a worker to subscribe to a PubSub topic and process messages as they're published:

```python
import asyncio
import launchflow as lf

worker = lf.gcp.ComputeEngineWorker("my-worker", machine_type="f1-micro")

topic = lf.gcp.PubsubTopic("my-topic")
subscription = lf.gcp.PubsubSubscription("my-subscription", topic=topic)

async def main():
    for async payload in subscription.async_pull():
        print(f"Got: {payload}")
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
```


### Jobs
Jobs are one-off tasks or workflows that run to completion.

For example, you might schedule a job to run every day at noon:

```python
import asyncio
import launchflow as lf

job = lf.gcp.CloudRunJob("my-worker", cron="0 12 * * *", machine_type="f1-micro")

async def main():
    print(f"Running job: {job.outputs().deployment_id}")
    await asyncio.sleep(5)
    print("Job complete.")

if __name__ == "__main__":
    asyncio.run(main())
```

<!-- {% tabProvider defaultLabel="GCP" %}
{% tabs %}
{% tab label="GCP" %}
1. Create a Dockerfile that can build and run your application.
2. Add a [Cloud Run](/reference/gcp-services/cloud-run) service to your `infra.py` file. Pass it the path to the Dockerfile you created if necessary (by default, it will search for one next to your `launchflow.yaml`).
3. Run `lf deploy` on the command line. This will prompt you to confirm the deployment, and create the following in GCP:
    - An [Artifact Registry](https://cloud.google.com/artifact-registry) repository to store the Docker image.
    - A [Cloud Build](https://cloud.google.com/build?hl=en) workflow to build and deploy it.
    - A [Load Balancer](https://cloud.google.com/load-balancing) to route traffic to it.
    - A [Cloud Run](https://cloud.google.com/run?hl=en) service to run it.
{% /tab %}
{% tab label="AWS" %}
1. Create a Dockerfile that can build and run your application.
2. Add a [ECS Fargate](/reference/aws-services/ecs-fargate) service to your `infra.py` file. Pass it the path to the Dockerfile you created if necessary (by default, it will search for one next to your `launchflow.yaml`).
3. Run `lf deploy` on the command line. This will prompt you to confirm the deployment, and create the following in AWS:
    - An [ECR](https://aws.amazon.com/ecr/) repository to store the Docker image.
    - A [CodeBuild](https://aws.amazon.com/codebuild/) workflow to build and deploy it.
    - An [Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) service to run it.
{% /tab %}
{% /tabs %}
{% /tabProvider %} -->


## CLI Commands

### Create a Deployment

```bash
lf deploy
```

### Delete a Deployment

```bash
lf destroy
```

### Promote a Deployment

```bash
lf promote [FROM_ENVIRONMENT] [TO_ENVIRONMENT]
```

### List Deployments

```bash
lf deployments list
```


For a full list of options see the command references:

- [lf deploy](/reference/cli#launchflow-deploy)
- [lf destroy](/reference/cli#launchflow-destroy)
- [lf promote](/reference/cli#launchflow-promote)
- [lf deployments](reference/cli#launchflow-deployments)
