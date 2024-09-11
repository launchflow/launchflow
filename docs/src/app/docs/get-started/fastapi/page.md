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

If you already have a FastAPI Project you can [skip to step #1](#1-initialize-launch-flow).

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

## 1. Initialize Launch Flow

{% lfInit /%}

---

## 2. Deploy your Service

{% deploy /%}

---

## 3. Cleanup your Resources

{% cleanup /%}

---

## 4. Visualize, Share, and Automate

{% lfcloud /%}

---

## What's next?

- View your application in the [LaunchFlow console](https://console.launchflow.com)
- Learn more about [Environments](/docs/concepts/environments), [Resources](/docs/concepts/resources), and [Services](/docs/concepts/services)
- Explore the [Resource Reference](/docs/reference/resources) to see all the resources you can create
- Join the [LaunchFlow Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) to ask questions and get help

<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /gettingStartedSelector %}
