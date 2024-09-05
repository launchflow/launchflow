---
title: FastAPI with LaunchFlow
nextjs:
  metadata:
    title: FastAPI with LaunchFlow
    description: Deploy FastAPI to AWS / GCP with LAunchflow
---

{% tabProvider defaultLabel="AWS" %}

## 1. Install LaunchFlow

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

## 2. Setup your project

#### Initialize LaunchFlow

Initialize LaunchFlow in a new directory.

```bash
mkdir launchflow-fastapi
cd launchflow-fastapi
lf init --backend=local
```

---

#### Authenticate with Cloud Providers

{% tabs %}
{% tab label="AWS" %}

LaunchFlow uses your local AWS credentials to manage and provision resources. We recommend using the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to authenticate with your AWS account. Once you have the CLI set up, run the following command to make sure you're authenticated:

```bash
aws sts get-caller-identity
```

{% /tab %}
{% tab label="GCP" %}

LaunchFlow uses your local GCP credentials to manage and provision resources. We recommend using the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) to authenticate with your GCP account. Once you have the CLI set up, run the following command to login to Google Cloud:

```bash
gcloud auth application-default login
```

{% /tab %}
{% /tabs %}

---


## 3. Create Your Application


Create a new file called `infra.py` and add a bucket to it.

{% tabs %}
{% tab label="AWS" %}

```python
import launchflow as lf

bucket = lf.aws.S3Bucket(f"new-bucket-{lf.project}-{lf.environment}")
```

{% /tab %}
{% tab label="GCP" %}

```python
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"new-bucket-{lf.project}-{lf.environment}")
```

{% /tab %}
{% /tabs %}

---


Create a new file called `main.py` with the following content:

```python
from fastapi import FastAPI
from infra import bucket

app = FastAPI()

@app.get("/")
def get_name(name: str):
    try:
        name_bytes = bucket.download_file("name.txt");
        return name_bytes.decode("utf-8")
    except:
        return f"{name} was not found"

@app.post("/")
def post_name(name: str):
    bucket.upload_from_string("name.txt", name)
    return "ok""
```

---

Create your bucket and cloud environment with:

```bash
lf create
```

Name your environment, select your cloud provider (`AWS` or `GCP`), and confirm the resources to be created.

---

Run the application locally with:

```bash
pip install fastapi[standard]
fastapi run main.py --port 8080
```

Upload and download a file to your bucket with:

```bash
curl -X POST http://localhost:8080?name=me
curl http://localhost:8080?name=me
```

---

## 4. Deploy Your Application

{% tabs %}

  {% tab label="AWS" %}

Create a `Dockerfile` next to your `main.py` file with the following content:

```Dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[aws] fastapi uvicorn

COPY ./main.py /code/main.py

ENV PORT=80
EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

Add ECS Fargate to your `infra.py` file:

```python,1,4+
import launchflow as lf

bucket = lf.aws.S3Bucket(f"new-bucket-{lf.project}-{lf.environment}")
ecs_fargate = lf.aws.ECSFargate("my-ecs-fargate")
```

---

Deploy your app to AWS with:

```bash
lf deploy my-env
```

---

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal-aws.png)

---

Once complete you will see a link to your deployed service on AWS Fargate.

![Deploy Result](/images/deploy-terminal-aws.png)


  {% /tab %}

  {% tab label="GCP" %}

Create a `Dockerfile` next to your `main.py` file with the following content:

```Dockerfile
FROM python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] fastapi uvicorn

COPY ./main.py /code/main.py

ENV PORT=8080

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

Add cloud run to your `infra.py` file:

```python,1,4+
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"new-bucket-{lf.project}-{lf.environment}")
cloud_run = lf.gcp.CloudRun("my-cloud-run")
```

---

Deploy your app to GCP with:

```bash
lf deploy my-env
```

---

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal.png)

---

Once complete you will see a link to your deployed service on GCP Cloud Run.

![Deploy Result](/images/deploy-terminal.png)

---
  {% /tab %}

{% /tabs %}

---

## 5. Visualize, Share, and Automate

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
