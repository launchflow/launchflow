---
title: Deploy Docker Image with Launchflow
nextjs:
  metadata:
    title: Deploy Docker Image with Launchflow
    description: Deploy a Docker container running Apache HTTP Server to AWS / GCP with LaunchFlow
---

{% gettingStartedSelector awsRuntimeOptions=["ECS Fargate"]  %}

{% gettingStartedSection cloudProvider="AWS" runtime="ECS Fargate" %}

Deploy a Docker Image to AWS Fargate with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/docker-get-started/aws/ecs-fargate).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

Deploy a Docker Image to GCP's serverless runtime Cloud Run with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/docker-get-started/gcp/cloud-run).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}

Deploy a Docker Image to GCP Compute Engine VMs with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/docker-get-started/gcp/compute-engine).

{% /callout %}

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

Deploy a Docker Image to Kubernetes running on GKE with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/docker-get-started/gcp/gke).

{% /callout %}

{% /gettingStartedSection %}

## 0. Set up your Dockerfile

If you already have a Dockerfile you can [skip to step #1](#1-initialize-launch-flow).

---

Create a new directory for your project.

```bash
mkdir launchflow-docker
cd lauchflow-docker
```

---

Create a file named `Dockerfile` with the following content:

{% gettingStartedSection cloudProvider="GCP" runtime="Kubernetes" %}

```Dockerfile
FROM httpd:2.4

RUN sed -i 's/Listen 80/Listen 8080/' /usr/local/apache2/conf/httpd.conf

RUN echo '<html>\n\
    <head>\n\
    <title>Hello from LaunchFlow</title>\n\
    </head>\n\
    <body>\n\
    <h1>Hello from LaunchFlow!</h1>\n\
    </body>\n\
    </html>' > /usr/local/apache2/htdocs/index.html
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Cloud Run" %}

```Dockerfile
FROM httpd:2.4

RUN sed -i 's/Listen 80/Listen 8080/' /usr/local/apache2/conf/httpd.conf

RUN echo '<html>\n\
    <head>\n\
    <title>Hello from LaunchFlow</title>\n\
    </head>\n\
    <body>\n\
    <h1>Hello from LaunchFlow!</h1>\n\
    </body>\n\
    </html>' > /usr/local/apache2/htdocs/index.html
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="AWS"}
```Dockerfile
FROM httpd:2.4

RUN echo '<html>\n\
    <head>\n\
    <title>Hello from LaunchFlow</title>\n\
    </head>\n\
    <body>\n\
    <h1>Hello from LaunchFlow!</h1>\n\
    </body>\n\
    </html>' > /usr/local/apache2/htdocs/index.html
```

{% /gettingStartedSection %}

{% gettingStartedSection cloudProvider="GCP" runtime="Compute Engine" %}
```Dockerfile
FROM httpd:2.4

RUN echo '<html>\n\
    <head>\n\
    <title>Hello from LaunchFlow</title>\n\
    </head>\n\
    <body>\n\
    <h1>Hello from LaunchFlow!</h1>\n\
    </body>\n\
    </html>' > /usr/local/apache2/htdocs/index.html
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

{% whatsnext /%}
<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /gettingStartedSelector %}
