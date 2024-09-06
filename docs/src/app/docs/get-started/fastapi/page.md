---
title: FastAPI with LaunchFlow
nextjs:
  metadata:
    title: FastAPI with LaunchFlow
    description: Deploy FastAPI to AWS / GCP with LAunchflow
---

Create a FastAPI backend that reads and writes to a S3 or GCS bucket and deploys to AWS ECS Fargate or GCP Cloud run.

{% callout type="note" %}

View the [entire source](https://github.com/launchflow/launchflow-examples/tree/main/fastapi-get-started) for this in our examples repo.

{% /callout %}

{% tabProvider defaultLabel="AWS" %}

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
    return f"Hello from {lf.environment}"
```

---

Create a `Dockerfile`:

{% tabs %}
{% tab label="AWS" %}
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

{% /tab %}
{% tab label="GCP" %}

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

{% /tab %}
{% /tabs %}

---


## 1. Initialize LaunchFlow

Install the LaunchFlow Python SDK and CLI using `pip`.

{% tabs %}
{% tab label="AWS" %}

```bash
pip install "launchflow[aws]"
```

{% /tab %}
{% tab label="GCP" %}

```bash
pip install "launchflow[gcp]"
```

{% /tab %}
{% /tabs %}

---

Initialize LaunchFlow in your project

```bash
lf init --backend=local
```

Creates a `launchflow.yaml` file and stores all your launchflow state in a local directory.

---

Create an `infra.py` file to define your infrastructure:

{% tabs %}
{% tab label="AWS" %}

```python
import launchflow as lf

bucket = lf.aws.S3Bucket(f"new-bucket-{lf.project}-{lf.environment}", force_destroy=True)
```

{% /tab %}
{% tab label="GCP" %}

```python
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"new-bucket-{lf.project}-{lf.environment}", force_destroy=True)
```

{% /tab %}
{% /tabs %}

---

## 2. Deploy your Application

{% tabs %}
{% tab label="AWS" %}

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


  {% /tab %}

  {% tab label="GCP" %}

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

  {% /tab %}

{% /tabs %}

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

{% /tabProvider %}
