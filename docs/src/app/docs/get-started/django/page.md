---
title: Deploy Django with LaunchFlow
nextjs:
  metadata:
    title: Deploy Django with LaunchFlow
    description: Deploy Django to AWS / GCP with LaunchFlow
---


{% gettingStartedSelector awsRuntimeOptions=["ECS Fargate"]  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Django application to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/django-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Django application to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/django-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Django application to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/django-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Django application to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/django-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}

## 0. Set up your Django Project

#### Initialize Django

Run the standard Django commands to create a new Django project and app.

```bash
mkdir launchflow-django
cd launchflow-django
django-admin startproject lfdjango .
python manage.py startapp app
```

---

Add a basic view to `app/views.py`:

```python
from django.http import HttpResponse
import launchflow as lf

def index(request):
    return HttpResponse(f"Hello from {lf.project}/{lf.environment}")
```

---

Add your view to `lfdjango/urls.py`:

```python
from django.urls import path
from app import views

urlpatterns = [
    path('', views.index, name='index'),
]
```

---

<!---
TODO update this to actually set the appropriate values
-->

Update `lfdjango/settings.py` to allow hosts:

```python
ALLOWED_HOSTS = ["*"]
```

You will want to change these in production later, but now lets just get things working.

---

Create a `Dockerfile` in your project root directory:

{% gettingStartedSection cloudProvider="AWS" %}

```Dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] django

COPY . /code/

ENV PORT=80
EXPOSE $PORT

CMD python manage.py runserver 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] django

COPY . /code/

ENV PORT=8080
EXPOSE $PORT

CMD python manage.py runserver 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] django

COPY . /code/

ENV PORT=8080
EXPOSE $PORT

CMD python manage.py runserver 0.0.0.0:$PORT
```
{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}
```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] django

COPY . /code/

ENV PORT=80
EXPOSE $PORT

CMD python manage.py runserver 0.0.0.0:$PORT
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
