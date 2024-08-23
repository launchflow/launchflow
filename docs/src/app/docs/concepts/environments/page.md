---
title: Environments
nextjs:
  metadata:
    title: Environments
    description: LaunchFlow Environments
---

{% mdimage src="/images/environments_light.svg" alt="diagram" className="block dark:hidden" height=250 width=600 /%}
{% mdimage src="/images/environments_dark.svg" alt="diagram" className="hidden dark:block" height=250 width=600 /%}

## Overview

<!-- TODO add more explanation about what we're creating for them -->
<!-- aws: -->
<!-- - artifact bucket for storing connection info / etc. -->
<!-- - iam role (used to authenticate with ersource and run all services) -->
<!-- - ecs cluster -->
<!-- - vpc -->
<!-- - aws internet gateway -->
<!-- - aws subnet -->
<!-- - aws route table (public and private) -->
<!-- - aws route table association -->

<!-- gcp -->
<!-- - artifact bucket -->
<!-- - gcp project -->
<!-- - vcp network -->
<!-- - service account and set up it's permissions -->
Environments group [Deployments](/docs/concepts/deployments) and [Resources](/docs/concepts/resources) inside a private network (VPC) on either GCP or AWS. You can create multiple environments for different stages of your workflow (e.g. development, staging, production) and switch between them with a single command.

## Environment Types

Environments can be created in two tiers: `development` and `production`. The tier of environment you create determines how your resources are auto configured.

### Development Environments
Development environments are used for testing and development. They auto configure your resources to be more cost-effective and manage firewall rules to let you connect to your resources from your local machine.

### Production Environments
Production environments are used for running your application in a secure and scalable way. They auto configure your resources for high availability and security, and ensure no connections are allowed from the public internet. Production environments are SOC 2 compliant by default.

## Permissions & Roles
Permissions & roles are managed for you, so you can easily create / connect to infrastructure across multiple environments without compromising security. Deployments can access any resource in the same environment, but cannot access resources in other environments. Resource clients automatically configure their connection settings based on the environment your code is running in.

## CLI Commands

For a full list of commands and options, see the [Environments Reference](/reference/cli#launchflow-environments).

### Create an Environment

```bash
lf environments create [ENVIRONMENT_NAME]
```

If this command fails for any reason you can re-run it with the same arguments to retrying creating the environment.

### Listing Environments

```bash
lf environments list
```

### Delete an Environment

```bash
lf environments delete [ENVIRONMENT_NAME]
```
