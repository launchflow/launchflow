---
title: GitHub Integration
nextjs:
  metadata:
    title: GitHub Integration
    description: Configure your app to deploy whenever a GitHub branch is pushed
---

{% callout type="note" %}

The LaunchFlow Cloud GitHub integration currently only supports GCP. AWS support will be coming soon, for more information please reach out to us at <team@launchflow.com>.

{% /callout %}

Using the LaunchFlow GitHub integration you can automatically deploy or promote your application whenever a branch or tag is pushed. This enables you to easily setup powerful CI/CD pipelines without needing to manage complex infrastructure.

- Deploy to a dev branch whenever a commit is merged into `main`
- Promote to production whenever the `prod` branch is updated

## How does it work?

The LaunchFlow GitHub integration works by connecting an environment to LaunchFlow cloud, installing the GitHub app to your repository, and than linking that repository with a LaunchFlow project. Once link you can add "Deploy Push Rules" to your project that define what environments to deploy to when a branch is pushed, or "Promote Push Rules" to define what environments from / to promote to when a branch is pushed.

When a matching rule is triggered LaunchFlow will kick off a deployment or promotion from that github ref. Building / promoting the docker image and updating the service will all take place in Cloud Build in your environments GCP
project.

{% callout type="note" %}

LaunchFlow uses Cloud Build to ensure that the cost of LaunchFlow remains low and to allow you to take advantage of cloud credits on GCP. This also helps maintain security and compliance by keeping your code and infrastructure in your own cloud project.

{% /callout %}

## Connecting an Environment

LaunchFlow Cloud will need access to your environment in order to deploy and promote services in your environment. To connect and environment simply run the following command:

```bash
lf cloud connect <ENV_NAME>
```

This command will connect LaunchFlow cloud to your environment. For GCP this will create a Service Account in your GCP project that LaunchFlow cloud will have access to use. The Service Account will be granted the minimum permissions needed to deploy services to GCP Cloud Run. You are free to review and modify the permissions as needed. You can delete this connection at anytime by running `lf destroy` and selecting the `LaunchFlowCloudReleaser` resource.

## Link a GitHub Repository

First you will need to link a GitHub repository to your LaunchFlow project. To link a GitHub repository visit the project in the [LaunchFlow Cloud Console](https://console.launchflow.com). Then visit the GitHub tab.

{% frameImage src="/images/github-tab.png" alt="GitHub Tab" height=200 /%}

If you have not connected your GitHub account you will need to login using your GitHub credentials.

{% callout type="note" %}
NOTE: the primary email address of your GitHub account must match the email address of your LaunchFlow account.

{% /callout %}

Next you will need to add the LaunchFlow GitHub app to any repositories you want to deploy from. Click the `Add GitHub Repositories` button to add the app to your repository.

{% frameImage src="/images/github-install.png" alt="GitHub Install" height=250 /%}

Once added you will need to link the repository to a LaunchFlow project. You can do this by clicking the `Link` button next to the repository you wish to deploy from.

{% frameImage src="/images/github-link.png" alt="GitHub Link" height=300 /%}

## Setup Push Rules

There are two types of push rules you can setup in LaunchFlow: **Deploy Push Rules** and **Promote Push Rules**. Deploy push rules will trigger the [deploy command](/refence/cli/#launchflow-deploy) to be run and promote push rules will trigger the [promote command](/reference/cli/#launchflow-promote) to be run.

For both types of push rules you can set the:

- branch or tag that should trigger the rule
- optionally you can provide an individual service to deploy / promote
- optionally you can provide a path to filter the push rule to only trigger when a specific path is updated

For deploy push rules you will also need to provide the enviroment to deploy to, and for promote push rules you will need to provide the `from` and `to` environments.

After you've linked the repository you can add a push rule. Click the `Add a rule` button to add any new push rules, once saved you can update or delete the rule later.

{% frameImage src="/images/github-push-rule.png" alt="GitHub Push Rule" height=400 /%}

## Monitoring Deployments

When a push rule is triggered LaunchFlow will kick off a GitHub deployment in the linked repository. You can monitor the status of the deployment in the GitHub UI. Each deployment will be grouped under the environment that it was being deployed or promoted to. From the GitHub UI you will be able to see links to the logs of the currently running deployment, the current status of the deployments, and a historical record of all deployments to your environments.

{% frameImage src="/images/github-deployment.png" alt="GitHub Deployment" height=300 /%}

### Notifications

If anything ever goes wrong with the deployment LaunchFlow will notify your team via email to let you know what went wrong. The email will contain links to the logs for you deployment allowing you to debu what went wrong. If you have any questions feel free to reach out to <team@launchflow.com>.

{% frameImage src="/images/github-email.png" alt="GitHub Email" height=400 /%}
