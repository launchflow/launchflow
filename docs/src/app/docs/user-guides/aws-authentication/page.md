---
title: AWS Authentication
nextjs:
  metadata:
    title: AWS Authentication
    description: Setup AWS authentication for LaunchFlow
---

LaunchFlow uses your local AWS credentials to manage and provision resources.
We recommend using the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) to authenticate with your AWS account.

## AWS User Credentials

1. [Create an IAM user in the AWS console](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html#id_users_create_console)
2. [Create security credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_CreateAccessKey) for your IAM user
3. Configure the AWS CLI with your IAM user credentials by running the following command:

```bash
aws configure
```

## SSO Credentials

You can also [setup AWS SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html) to authenticate with your AWS account.
This method is more complicated to setup but is more secure because no long-term credentials are stored on your machine.

## Verify Credentials

At any time you can run the following command to verify that you are authenticated with AWS:

```bash
aws sts get-caller-identity
```
