---
title: GCP Authentication
nextjs:
  metadata:
    title: GCP Authentication
    description: Setup GCP authentication for LaunchFlow
---

## Local Authentication

LaunchFlow uses your local GCP credentials to manage and provision resources. For local development
we recommend installing the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install). Once installed
LaunchFlow requires you setup application default credentials using the following command:

```bash
gcloud auth application-default login
```

These credentials are short lived so you will need to run this command periodically to refresh your credentials.

Your GCP credentials will only ever be used locally and will never be sent to LaunchFlow Cloud if you are using
LaunchFlow cloud.

## Service Account Authentication

If you are using LaunchFlow in non-interactive setting such as a CI/CD pipeline, you can authenticate using a service account by
using a [service account key](https://cloud.google.com/docs/authentication/provide-credentials-adc#local-key) or [workflow identity federation](https://cloud.google.com/iam/docs/workload-identity-federation)
depending on the environment you are running LaunchFlow in.
