---
title: FastAPI with LaunchFlow
nextjs:
  metadata:
    title: FastAPI with LaunchFlow
    description: Deploy FastAPI to AWS / GCP with Launchflow
---

{% gettingStartedSelector  %}


{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a FastAPI application to AWS Fargate with LaunchFlow.

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a FastAPI application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a FastAPI application to GCP Compute Engine VMs with LaunchFlow.

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a FastAPI application to Kubernetes running on GKE with LaunchFlow.

{% /gettingStartedSection %}

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/fastapi-get-started).

{% /callout %}

## 0. Setup your FastAPI Project

If you already have a FastAPI Project you can skip to step [#1](#1-initialize-launch-flow).

---

Initialize a new directory for your project

```bash
mkdir launchflow-fastapi
cd launchflow-fastapi
```

---

Create a `main.py`:

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index(name: str = ""):
    return f"Hello from {lf.project}/{lf.environment}"
```

---

Create a `Dockerfile`:

{% gettingStartedSection cloudProvider="AWS" %}
```dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[aws] fastapi[standard]

COPY ./main.py /code/main.py

ENV PORT=80
EXPOSE $PORT

CMD fastapi run --host 0.0.0.0 --port $PORT
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" %}

```dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] fastapi[standard]

COPY ./main.py /code/main.py

ENV PORT=8080
EXPOSE $PORT

CMD fastapi run main.py --host 0.0.0.0 --port $PORT
```

{% /gettingStartedSection %}

---


## 1. Initialize LaunchFlow

Install the LaunchFlow Python SDK and CLI using `pip`.

{% gettingStartedSection cloudProvider="AWS" %}

```bash
pip install "launchflow[aws]"
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" %}

```bash
pip install "launchflow[gcp]"
```

{% /gettingStartedSection %}

---

Initialize LaunchFlow in your project

```bash
lf init --backend=local
```

This command creates a `launchflow.yaml` file and stores all your launchflow state in a local directory.

---

Create an `infra.py` file to define your service:

{% gettingStartedSection cloudProvider="AWS" %}

```python
import launchflow as lf

service = lf.aws.ECSFargate("my-service")
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" %}

```python
import launchflow as lf

service = lf.gcp.CloudRun("my-service")
```

{% /gettingStartedSection %}

---

## 2. Deploy your Application

{% gettingStartedSection cloudProvider="AWS" %}

Deploy your app to AWS:

```bash
lf deploy
```

Name your environment, select your cloud provider (`AWS`), and confirm the resources to be created, and service to deploy.

---

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal-aws.png)

---

Once complete you will see a link to your deployed service on AWS Fargate.

![Deploy Result](/images/deploy-terminal-aws.png)


{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" %}

Deploy your app to GCP:

```bash
lf deploy
```

Name your environment, select your cloud provider (`GCP`), and confirm the resources to be created, and service to deploy.

---

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal.png)

---

Once complete you will see a link to your deployed service on GCP Cloud Run.

![Deploy Result](/images/deploy-terminal.png)

{% /gettingStartedSection %}

---

## 3. Clean up your resources

Optionally you can delete all your resources, service, and environments with:

```bash
lf destroy
lf environment delete
```

## 4. Visualize, Share, and Automate

![LaunchFlow Console](/images/console.png)

{% callout type="note" %}
LaunchFlow Cloud usage is optional and free for individuals.
{% /callout %}

 Using the local backend like we did above works fine for starting a project, but doesn't offer a way to share state between multiple users. LaunchFlow Cloud is a web-based service for managing, sharing, and automating your infrastructure. It's free for individuals and provides a simple, secure way to collaborate with your team and automate your release pipelines.

Sign up for LaunchFlow Cloud and connect your local environment by running:

```bash
lf init --backend=lf
```

This will create a project in your LaunchFlow Cloud account and migrate your local state to the LaunchFlow Cloud backend.

## What's next?

- View your application in the [LaunchFlow console](https://console.launchflow.com)
- Learn more about [Environments](/docs/concepts/environments), [Resources](/docs/concepts/resources), and [Services](/docs/concepts/services)
- Explore the [Resource Reference](/docs/reference/resources) to see all the resources you can create
- Join the [LaunchFlow Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) to ask questions and get help

<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /gettingStartedSelector %}
