---
title: Deploy Flask with LaunchFlow
nextjs:
  metadata:
    title: Deploy Flask with LaunchFlow
    description: Deploy Flask to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Flask application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/flask-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Flask application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/flask-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Flask application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/flask-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Flask application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/flask-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}

## 0. Set up your Flask Project

If you already have a Flask Project you can [skip to step #1](#1-initialize-launch-flow).

---

Initialize a new directory for your project

```bash
mkdir launchflow-flask
cd launchflow-flask
```

---

Create a `main.py`:

```python
from flask import Flask, request
import launchflow as lf

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return f"Hello from {lf.project}/{lf.environment}"
```

---

Create a `Dockerfile` next to `main.py`:

{% gettingStartedSection cloudProvider="AWS" %}

```Dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[aws] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=80
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=8080
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=8080
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=80
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
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

{% /gettingStartedSelector  %}
