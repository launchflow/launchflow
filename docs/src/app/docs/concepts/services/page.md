---
title: Services
nextjs:
  metadata:
    title: Services
    description: LaunchFlow Services
---


{% mdimage src="/images/services_light.svg" alt="diagram" className="block dark:hidden" height=250 width=600 /%}
{% mdimage src="/images/services_dark.svg" alt="diagram" className="hidden dark:block" height=250 width=600 /%}


## Overview


Services allow you to deploy a application with minimal configuration. Given your application code and a Dockerfile to run it, LaunchFlow will setup a deployment pipeline including:

{% tabProvider defaultLabel="GCP" %}
{% tabs %}
{% tab label="GCP" %}
1. Create a Dockerfile that can build and run your application.
1. Add a [Cloud Run](/reference/gcp-services/cloud-run) service to your `infra.py` file. Pass it the path to the Dockerfile you created if necessary (by default, it will search for one next to your `launchflow.yaml`).
1. Run `lf deploy` on the command line. This will prompt you to confirm the deployment, and create the following in GCP:
    - An [Artifact Registry](https://cloud.google.com/artifact-registry) repository to store the Docker image.
    - A [Cloud Build](https://cloud.google.com/build?hl=en) workflow to build and deploy it.
    - A [Load Balancer](https://cloud.google.com/load-balancing) to route traffic to it.
    - A [Cloud Run](https://cloud.google.com/run?hl=en) service to run it.
{% /tab %}
{% tab label="AWS" %}
1. Create a Dockerfile that can build and run your application.
1. Add a [ECS Fargate](/reference/aws-services/ecs-fargate) service to your `infra.py` file. Pass it the path to the Dockerfile you created if necessary (by default, it will search for one next to your `launchflow.yaml`).
1. Run `lf deploy` on the command line. This will prompt you to confirm the deployment, and create the following in AWS:
    - An [ECR](https://aws.amazon.com/ecr/) repository to store the Docker image.
    - A [CodeBuild](https://aws.amazon.com/codebuild/) workflow to build and deploy it.
    - An [Fargate](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html) service to run it.
{% /tab %}
{% /tabs %}
{% /tabProvider %}


## CLI Commands

### Create a Service

```bash
lf deploy
```

### Delete a Service

```bash
lf destroy
```

### List Services

```bash
lf services list
```

### Promote a Service

```bash
lf promote [FROM_ENVIRONMENT] [TO_ENVIRONMENT]
```

For a full list of options see the command references:

- [lf deploy](/reference/cli#launchflow-deploy)
- [lf destroy](/reference/cli#launchflow-destroy)
- [lf services](reference/cli#launchflow-services)
- [lf promote](/reference/cli#launchflow-promote)
