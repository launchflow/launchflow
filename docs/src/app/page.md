---
title: LaunchFlow Docs
subtitle: Launch websites, APIs, and workers to AWS / GCP with minimal configuration
---

LaunchFlow is an open source command line tool that deploys applications to AWS, GCP, and Docker (local) with minimal setup. All of the deployment options are configured by default, but fully customizable.

Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated VPC environment in your cloud account.

LaunchFlow runs entirely on your local machine and everything is created in your own cloud account. Follow the [Get Started Guide](/docs/get-started) to launch an example API in minutes.

## Get Started

Get started with the framework of your choice or any Docker image.

{% gettingStartedSearch /%}

## Core Concepts

[Services](/docs/concepts/services) allow you to deploy websites, APIs, workflows, and other types of applications to your cloud account with minimal setup. All you need to provide is a Dockerfile, then LaunchFlow will take care of the rest.

[Resources](/docs/concepts/resources) allow you to add databases, storage, task queues, and more to your application by simply importing them in your code.

[Environments](/docs/concepts/environments) manage the networking, permissions, and configuration of your **Services** and **Resources** inside a dedicated VPC. You can switch between environments with a single command.

## Framework Integrations

{% callout type="note" %}
The integrations below are only available for Python applications.

LaunchFlow can deploy any type of application, but Python applications benefit from deeper integrations with the SDK.

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
