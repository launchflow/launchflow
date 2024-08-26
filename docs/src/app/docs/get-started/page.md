---
title: Get Started with LaunchFlow
nextjs:
  metadata:
    title: Get Started
    description: Get started with LaunchFlow
---

<!-- TODO use the fence highlighting to show the lines that were modified-->
<!-- would be nice to modify it to show additions in green and deletions in red -->
LaunchFlow is an open source deployment tool that makes it easy to automate your application's infrastructure, secrets, and deployments on Amazon Web Services (AWS) and Google Cloud Platform (GCP). For an overview, see the [welcome page](../).


In this walk-through, we'll install LaunchFlow and demonstrate how to create and deploy a small web application with it. See [here](../#core-concepts) an overview of the core concepts.

<!-- TODO: move tab provider so we only have one set of tabs at the top that's sticky like https://docs.stripe.com/checkout/quickstart -->
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

## 2. Setup your local environment

### Initialize LaunchFlow

Use the CLI to set up your local workspace.

```bash
lf init --backend=local
```

Running the command will create a `launchflow.yaml` file that configures your application. The `--backend=local` flag tells LaunchFlow to store configuration and state information locally.

The file will look something like this:

```yaml
project: your-project-name
backend: file://.launchflow
```

You can learn more about it in the [launchflow.yaml docs](/reference/launchflow-yaml).

### Authenticate with Cloud Providers

{% tabs %}

{% tab label="AWS" %}

LaunchFlow uses your local AWS credentials to manage and provision resources. We recommend using the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to authenticate with your AWS account. Once you have the CLI set up, run the following command to login to your AWS account:

```bash
aws sts get-caller-identity
```

Your credentials never leave your local machine. LaunchFlow runs everything on your client and encrypts your infrastructure state at rest.

{% /tab %}

{% tab label="GCP" %}

LaunchFlow uses your local GCP credentials to manage and provision resources. We recommend using the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) to authenticate with your GCP account. Once you have the CLI set up, run the following command to login to your Google Cloud account:

```bash
gcloud auth application-default login
```

Your credentials never leave your local machine. LaunchFlow runs everything on your client and encrypts your infrastructure state at rest.

{% /tab %}


{% /tabs %}


## 3. Launch Your Application

### Create a FastAPI Application

Let's start out by creating a simple FastAPI application.

_main.py_:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def index():
    return "Hello World"
```

To run the application locally, we need to install some dependencies:

```bash
pip install fastapi uvicorn
```

Then run it with:

```bash
uvicorn main:app --port 8080
```

If everything is set up correctly, sending a GET request to `http://localhost:8080/` should return a response with the value `Hello World`. Let's integrate some cloud infrastructure using LaunchFlow!

### Add a Storage Bucket with LaunchFlow

{% tabs %}

  {% tab label="AWS" %}
Import the LaunchFlow S3Bucket resource and create and instance in your Python code:

_main.py_:
```python,1,4+,10+,11+,12+
from fastapi import FastAPI
import launchflow as lf

bucket = lf.aws.S3Bucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents
```

Before we can run it again, we need to do two things:

1. Create a LaunchFlow [Environment](/docs/concepts/environments), which will group together the infrastructure we're going to create.
1. Provision the [Resources](/docs/concepts/resources) that our code is using.

We can do both by running one command:
```bash
lf create
```

Follow the prompts to:

1. Select AWS as the cloud provider you want to use and choose an environment name
1. Confirm that you'd like to create the RDSPostgres resource

If you see `Successfully created 1 resource`, you're ready to run the application again! LaunchFlow resources are uniquely identified by their name and environment, so to run the code locally now, we need to pass through the environment name. This is what the `lf run` command runner is for:

```bash
lf run {your environment name} -- uvicorn main:app --port 8080
```

Sending a GET request to `http://localhost:8080/` should return you another `Hello World` response!
  {% /tab %}

  {% tab label="GCP" %}
Import the LaunchFlow GCSBucket resource and create and instance in your Python code:

_main.py_:
```python,1,4+,10+,11+,12+
from fastapi import FastAPI
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents
```

Before we can run it again, we need to do two things:

1. Create a LaunchFlow [Environment](/docs/concepts/environments), which will group together the infrastructure we're going to create.
1. Provision the [Resources](/docs/concepts/resources) that our code is using.

We can do both by running one command:
```bash
lf create
```

Follow the prompts to:

1. Select GCP as the cloud provider you want to use and choose an environment name
1. Confirm that you'd like to create the CloudSQLPostgres resource

If you see `Successfully created 1 resource`, you're ready to run the application again! LaunchFlow resources are uniquely identified by their name and environment, so to run the code locally now, we need to pass through the environment name. This is what the `lf run` command runner is for:

```bash
lf run {your environment name} -- uvicorn main:app --port 8080
```

Sending a GET request to `http://localhost:8080/` should return you another `Hello World` response!
  {% /tab %}

{% /tabs %}

### Deploy Your Application

Now that we have it all working locally, let's deploy it to the cloud!

{% tabs %}

  {% tab label="AWS" %}
We can deploy to [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) with minimal setup. You'll need to provide a Dockerfile that can run your code.
```python,1,14+
from fastapi import FastAPI
import launchflow as lf

bucket = lf.aws.S3Bucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents

ecs_fargate = lf.aws.ECSFargate("my-ecs-fargate")
```

```Dockerfile
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -U pip setuptools wheel && pip install --no-cache-dir launchflow[aws] fastapi uvicorn

COPY ./main.py /code/main.py

ENV PORT=8080

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
```
  {% /tab %}

  {% tab label="GCP" %}
We can deploy to [Cloud Run](https://cloud.google.com/run). You'll need to provide a Dockerfile that can run your code.
```python,1,14+
from fastapi import FastAPI
import launchflow as lf

bucket = lf.gcp.GCSBucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents

cloud_run = lf.gcp.CloudRun("my-cloud-run", region="us-central1")
```

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
  {% /tab %}

{% /tabs %}


<!-- TODO show filenames -->
LaunchFlow will set up a Cloud Run Service and Docker build pipeline for you when you run:

```bash
lf deploy my-env
```

You should see a link to your deployed service if all went well, and logs to debug any issues that may have occurred. That's it!

<!-- TODO add a bit more detail about what the success case will print -->

Learn more about the deploy command [here](/reference/cli#launchflow-deploy).

### Switch Environments

One of the benefits of LaunchFlow is the ability to replicate your application across multiple environments. To create a staging version of your application, just run `lf deploy` again with a different environment name:

```bash
lf deploy my-new-env
```

By default, the `lf deploy` command will also run `lf create` for you. This means you can deploy your entire application to a new environment by simply changing the environment name. Learn more about environments [here](/docs/concepts/environments).

## 4. Visualize, Share, and Automate

{% callout type="note" %}
LaunchFlow Cloud usage is optional and free for individuals.
{% /callout %}

 Using the local backend like we did above works fine for starting a project, but doesn't offer a way to share state between multiple users. LaunchFlow Cloud is a web-based service for managing, sharing, and automating your infrastructure. It's is free for individuals and provides a simple, secure way to collaborate with your team and automate your release pipelines.

Sign up for LaunchFlow Cloud and connect your local environment by running:

```bash
lf init --backend=lf
```

This will create a project in your account and migrate your local state to LaunchFlow Cloud.

## What's next?

- View your application in the [LaunchFlow console](https://console.launchflow.com)
- Learn more about [Environments](/docs/concepts/environments), [Resources](/docs/concepts/resources), and [Services](/docs/concepts/services)
- Explore the [Resource Reference](/docs/reference/resources) to see all the resources you can create
- Join the [LaunchFlow Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-27wlowsza-Uiu~8hlCGkvPINjmMiaaMQ) to ask questions and get help

<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /tabProvider %}