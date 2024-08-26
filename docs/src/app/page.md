---
title: Welcome
---

LaunchFlow is an open source deployment tool that makes it easy to automate your application's infrastructure, secrets, and deployments on Amazon Web Services (AWS) and Google Cloud Platform (GCP).

Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated environment in your cloud account.

LaunchFlow runs entirely on your local machine and everything is created in your own cloud account. Follow the [Get Started Guide](/docs/get-started) to launch an example API in minutes.


{% callout type="note" %}
**LaunchFlow is not just for deploying Python apps.**

The Python SDK is used to define your infrastructure in code, but you can deploy any static or Dockerized application to AWS or GCP.

Python is just the language for your DevOps automation.

{% /callout %}

## Core Concepts

[Services](/docs/concepts/services) allow you to deploy websites, APIs, workflows, and other types of applications to your cloud account with minimal setup. All you need to provide is a Dockerfile - LaunchFlow will take care of the rest.

[Resources](/docs/concepts/resources) allow you to add things like databases, storage, and task queues to your application by simply importing them in your code.

[Environments](/docs/concepts/environments) manage the networking, permissions, and configuration of your **Services** and **Resources** inside a dedicated VPC.


{% quick-links %}

{% quick-link title="Get Started" icon="lightbulb" href="/docs/get-started" description="Get Started with LaunchFlow" /%}

{% quick-link title="Example Backend" icon="lightbulb" href="/examples/fastapi/simple-crud-api" description="Create a simple API with LaunchFlow" /%}

{% /quick-links %}

## Framework Integrations

{% callout type="note" %}
The integrations below are only available for Python applications.

We will add support for more languages in the future.
{% /callout %}

LaunchFlow provides integrations with popular Python frameworks to make it easy to connect to cloud resources inside your application. These integrations are optional and can be used to remove most of the boilerplate code needed to connect to AWS / GCP services.

- [FastAPI](/docs/framework-guides/fastapi)
- [Flask](/docs/framework-guides/flask)
- [Django](/docs/framework-guides/django)
- [SQLAlchemy](/docs/framework-guides/sqlalchemy)

## Need Help?

If you have any questions or need help getting started, please email [team@launchflow.com](mailto:team@launchflow.com) or join our [slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-280e6a5ck-zfCrKbqw5w89L~0Xl55G4w).

We are always happy to help and would love to hear from you!
