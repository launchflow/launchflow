---
title: Deploy Docker Image with Launchflow
nextjs:
  metadata:
    title: Deploy Docker Image with Launchflow
    description: Deploy a Docker container running Apache HTTP Server to AWS / GCP with LaunchFlow
---

LaunchFlow can be used to deploy any containerized application to AWS ECS Fargate or GCP Cloud Run. This guide demonstrates how to deploy a Docker container running Apache HTTP Server to AWS or GCP.

{% callout type="note" %}

View the [entire source](https://github.com/launchflow/launchflow-examples/tree/main/docker-get-started) for this in our examples repo.

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
mkdir launchflow-docker
cd launchflow-docker
lf init --backend=local
```

---

## 3. Create Application

Create a `index.html` with the following content:

```html
<html>
    <head>
        <title>Hello from LaunchFlow</title>
    </head>
    <body>
        <h1>Hello from LaunchFlow!</h1>
    </body>
</html>
```

---

Create a file named `Dockerfile` with the following content:

```Dockerfile
FROM httpd:2.4

COPY ./index.html /usr/local/apache2/htdocs/index.html
```

---

## 4. Define Your Infrastructure

Create a new file called `infra.py` with the following content:

{% tabs %}
{% tab label="AWS" %}

```python
import launchflow as lf

ecs_fargate = lf.aws.ECSFargate("my-service")
```

{% /tab %}
{% tab label="GCP" %}

```python
import launchflow as lf

cloud_run = lf.gcp.CloudRun("my-service", port=80)
```

{% /tab %}
{% /tabs %}

---

## 5. Deploy Your Application

Before running the following command, make sure you have your [AWS credentials](/docs/user-guides/aws-authentication) or [GCP credentials](/docs/user-guides/gcp-authentication) configured.

Deploy your app to the cloud:

```bash
lf deploy
```

Name your environment, select your cloud provider (`AWS` or `GCP`), and confirm the resources to be created / deployed.

Once complete, you will see a link to your deployed service.

---

## 6. Clean up your resources

Optionally, you can delete all your resources, service, and environments with:

```bash
lf destroy
lf environment delete
```

## 7. Visualize, Share, and Automate

![LaunchFlow Console](/images/console.png)

{% callout type="note" %}
LaunchFlow Cloud usage is optional and free for individuals.
{% /callout %}

LaunchFlow Cloud is a web-based service for managing, sharing, and automating your infrastructure. It's free for individuals and provides a simple, secure way to collaborate with your team and automate your release pipelines.

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

{% /tabProvider %}
