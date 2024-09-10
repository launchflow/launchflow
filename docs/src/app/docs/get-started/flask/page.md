---
title: Flask with LaunchFlow
nextjs:
  metadata:
    title: Flask with LaunchFlow
    description: Deploy Flask to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector  %}

Create a Flask backend that reads and writes to a S3 or GCS bucket and deploys to AWS ECS Fargate or GCP Cloud run.

{% callout type="note" %}

View the [entire source](https://github.com/launchflow/launchflow-examples/tree/main/flask-get-started) for this in our examples repo.

{% /callout %}

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
mkdir launchflow-flask
cd launchflow-flask
lf init --backend=local
```

---

## 3. Create Your Application

Create a new file called `infra.py` and add a bucket to it.

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

Create a new file called `main.py` with the following content:

```python
from flask import Flask, request
from infra import bucket

app = Flask(__name__)

@app.route("/", methods=["GET"])
def get_name():
    name = request.args.get("name")
    if not name:
        return "Please provide a name"
    try:
        name_bytes = bucket.download_file(f"{name}.txt")
        return name_bytes.decode("utf-8")
    except:
        return f"{name} was not found"

@app.route("/", methods=["POST"])
def post_name():
    name = request.args.get("name")
    if not name:
        return "Please provide a name"
    bucket.upload_from_string(name, f"{name}.txt")
    return "ok"
```

---

Create your bucket and cloud environment. Before running the following command, make sure you have your [AWS credentials](/docs/user-guides/aws-authentication) or [GCP credentials](/docs/user-guides/gcp-authentication) configured.

```bash
lf create
```

Name your environment, select your cloud provider (`AWS` or `GCP`), and confirm the resources to be created.

---

Run the application locally, replace `ENV_NAME` with the name you gave your environment in the previous step:

```bash
pip install flask gunicorn
lf run $ENV_NAME -- gunicorn  main:app -b 0.0.0.0:8080
```

---

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
RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[aws] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=80
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
```

---

Add ECS Fargate to your `infra.py` file:

```python,1,4+
import launchflow as lf

bucket = lf.aws.S3Bucket(f"new-bucket-{lf.project}-{lf.environment}")
ecs_fargate = lf.aws.ECSFargate("my-ecs-fargate")
```

---

Deploy your app to AWS:

```bash
lf deploy
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

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[gcp] flask gunicorn

COPY ./main.py /code/main.py
COPY ./infra.py /code/infra.py

ENV PORT=8080
EXPOSE $PORT

CMD gunicorn  main:app -b 0.0.0.0:$PORT
```

---

Add cloud run to your `infra.py` file:

```python,1,4+
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"new-bucket-{lf.project}-{lf.environment}")
cloud_run = lf.gcp.CloudRun("my-cloud-run")
```

---

Deploy your app to GCP:

```bash
lf deploy
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

## 5. Clean up your resources

Optionally you can delete all your resources, service, and environments with:

```bash
lf destroy
lf environment delete
```

## 6. Visualize, Share, and Automate

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

{% gettingStartedSelector  %}
