---
title: Get Started with LaunchFlow
nextjs:
  metadata:
    title: Get Started
    description: Get started with LaunchFlow
---

<!-- TODO use the fence highlighting to show the lines that were modified-->
<!-- would be nice to modify it to show additions in green and deletions in red -->
LaunchFlow is an open source Python SDK that lets you deploy websites, APIs, and other applications to AWS / GCP with minimal configuration. See the [welcome page](../) for an overview.

Follow this guide to launch a FastAPI app to [ECS Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) on AWS or [Cloud Run](https://cloud.google.com/run) on GCP. 

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

Running the command will create a `launchflow.yaml` file that looks like this:

```yaml
project: your-project-name
backend: file://.launchflow
```

The `--backend=local` flag tells LaunchFlow to store configuration and state information locally. You can also use a cloud storage like Google Cloud Storage, S3 (coming soon), or LaunchFlow Cloud.

You can learn more about it in the [launchflow.yaml docs](/reference/launchflow-yaml).

### Authenticate with Cloud Providers

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

If everything is set up correctly, you should see `Hello World` when you visit `http://localhost:8080/` in your browser.


### Deploy Your Application

Now that we have a working app, let's deploy it to the cloud!

{% tabs %}

  {% tab label="AWS" %}

First we'll need a `Dockerfile` to tell LaunchFlow how to build your application.

_Dockerfile_:
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

The only thing left to do is add the [ECSFargate Service](/reference/aws-services/ecs-fargate) somewhere in your project directory. LaunchFlow will handle networking, security, and deployment configuration for you.

```python,1,2+,3+,4+
from fastapi import FastAPI
import launchflow as lf

ecs_fargate = lf.aws.ECSFargate("my-ecs-fargate")

app = FastAPI()

@app.get("/")
def index():
    return "Hello World"

```

{% callout type="note" %}
We recommend using a single `infra.py` file to define your infrastructure, but you are free to use LaunchFlow anywhere in your project. 

We're using a single file here for simplicity.
{% /callout %}

LaunchFlow will set up a Fargate Service and Docker build pipeline for you when you run:

```bash
lf deploy my-env
```

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal-aws.png)

If everything goes well, you should see a link to your deployed service and logs to debug any issues that may have occurred.

![Deploy Plan](/images/deploy-terminal-aws.png)

  {% /tab %}

  {% tab label="GCP" %}

First we'll need a `Dockerfile` to tell LaunchFlow how to build your application.

_Dockerfile_:
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

The only thing left to do is add the [CloudRun Service](/reference/gcp-services/cloud-run) somewhere in your project directory. LaunchFlow will handle networking, security, and deployment configuration for you.

```python,1,2+,3+,4+
from fastapi import FastAPI
import launchflow as lf

cloud_run = lf.gcp.CloudRun("my-cloud-run")

app = FastAPI()

@app.get("/")
def index():
    return "Hello World"
```

{% callout type="note" %}
We recommend using a single `infra.py` file to define your infrastructure, but you are free to use LaunchFlow anywhere in your project. 

We're using a single file here for simplicity.
{% /callout %}

LaunchFlow will set up a Cloud Run Service and Docker build pipeline for you when you run:

```bash
lf deploy my-env
```

You will be able to view the plan and confirm before the resources are created.
![Deploy Plan](/images/plan-terminal.png)

If everything goes well, you should see a link to your deployed service and logs to debug any issues that may have occurred.

![Deploy Plan](/images/deploy-terminal.png)

  {% /tab %}

{% /tabs %}

That's all there is to it!

<!-- TODO add a bit more detail about what the success case will print -->

Learn more about the deploy command [here](reference/cli#lf-deploy).

### Add Cloud Resources

LaunchFlow makes it easy to add databases, task queues, and other cloud resources to your application. Your [Services](/docs/concepts/services) automatically have access to any [Resources](/docs/concepts/resources) you create alongside them in the same [Environment](/docs/concepts/environments).

{% tabs %}

  {% tab label="AWS" %}
To add storage bucket to your application, simply import a LaunchFlow S3Bucket resource anywhere in your Python code. You can even use it inside your application code if you want!

_main.py_:
```python,1,6+,7+,13+,14+,15+,16+
from fastapi import FastAPI
import launchflow as lf

my_service = lf.aws.ECSFargate("my-ecs-fargate")

# NOTE: The bucket name must be globally unique
bucket = lf.aws.S3Bucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
    # Read / Write to the bucket to test it out 
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents
```

Rerun the `lf deploy` command to create the S3Bucket resource and update the ECSFargate service with the new code.

```bash
lf deploy my-env
```

You can also run your application locally with the `lf run` command:

```bash
lf run my-env -- uvicorn main:app --port 8080
```

Visit `http://localhost:8080/` to see the updated response!

  {% /tab %}

  {% tab label="GCP" %}
To add storage bucket to your application, simply import a LaunchFlow GCSBucket resource anywhere in your Python code. You can even use it inside your application code if you want!

_main.py_:
```python,1,6+,7+,13+,14+,15+,16+
from fastapi import FastAPI
import launchflow as lf

my_service = lf.gcp.CloudRun("my-cloud-run")

# NOTE: The bucket name must be globally unique
bucket = lf.gcp.GCSBucket(f"my-get-started-bucket-{lf.environment}")

app = FastAPI()

@app.get("/")
def index():
  # Read / Write to the bucket to test it out 
    bucket.upload_from_string("Hello World", "hello_world.txt")
    contents = bucket.download_file("hello_world.txt")
    return contents
```

Rerun the `lf deploy` command to create the GCSBucket resource and update the CloudRun service with the new code.

```bash
lf deploy my-env
```

You can also run your application locally with the `lf run` command:

```bash
lf run my-env -- uvicorn main:app --port 8080
```

Visit `http://localhost:8080/` to see the updated response!
  {% /tab %}

{% /tabs %}

### Switch Environments

One of the main benefits of LaunchFlow is the ability to easily replicate your application across multiple environments. To create a staging version of your application, just run `lf deploy` again with a different environment name:

```bash
lf deploy my-staging-env
```

You can easily customize dynamic configuration across environments using the `lf.environment` global variable in your code.

```python

force_destroy = True
desired_count = 1

# Set different configurations based on the environment
if lf.environment == "production":
    force_destroy = False
    desired_count = 2

bucket = lf.aws.S3Bucket("my-bucket", force_destroy=force_destroy)
api = lf.aws.ECSFargate("my-ecs-fargate", desired_count=desired_count)
```

See the [GitHub Integration](/docs/launchflow-cloud/github-deployments) to learn how to automate deployments between environments on git push.


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
