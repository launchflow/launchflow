---
title: Deploy to AWS Lambda with LaunchFlow
nextjs:
  metadata:
    title: Deploy to AWS Lambda with LaunchFlow
    description: Deploy and manage AWS Lambda functions using LaunchFlow.
---

{% gettingStartedSelector awsRuntimeOptions=["Lambda"] gcpRuntimeOptions=[] %}

{% gettingStartedSection cloudProvider="AWS" runtime="Lambda" %}

Deploy a serverless API on AWS Lambda with LaunchFlow.

{% callout type="note" %}

View the source code for this guide in our [examples repo](https://github.com/launchflow/launchflow-examples/tree/main/aws-lambda).

{% /callout %}

{% /gettingStartedSection %}

---

## 0. Create your Lambda function

If you already have an existing Lambda function, you can [skip to step #1](#1-initialize-launch-flow).

Create a new directory for your project.

```bash
mkdir launchflow-lambda
cd launchflow-lambda
```

---

Create a file named `app.py` with the following content:

```python
def handler(event, context):
    return {
        "statusCode": 200,
        "body": "Hello from LaunchFlow!"
    }
```

---

## 1. Initialize Launch Flow

{% lfInit /%}

---

Update the LambdaService in your `infra.py` file to point to your Lambda handler in `app.py`

```python,1,4+
import launchflow as lf

# LambdaService Docs: https://docs.launchflow.com/reference/aws-services/lambda-service
api = lf.aws.LambdaService("my-lambda-api", handler="app.handler")
```

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

- View your application in the [LaunchFlow console](https://console.launchflow.com)
- Learn more about [Environments](/docs/concepts/environments), [Resources](/docs/concepts/resources), and [Services](/docs/concepts/services)
- Explore the [Resource Reference](/docs/reference/resources) to see all the resources you can create
- Join the [LaunchFlow Slack community](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ) to ask questions and get help

<!-- - Checkout out our [example applications](/examples) to see even more way to use LaunchFlow. -->

{% /gettingStartedSelector %}
