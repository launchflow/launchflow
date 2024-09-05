---
title: LaunchFlow Cloud
nextjs:
  metadata:
    title: LaunchFlow Cloud
    description: LaunchFlow Cloud
---

{% mdimage src="/images/console.png" alt="diagram"  /%}

## Overview

LaunchFlow Cloud is an optional service that makes it easier to manage and collaborate on your LaunchFlow projects.

## Projects

LaunchFlow Cloud Projects allow you to organize multiple [Environments](/docs/concepts/environments) for your application (e.g. development, staging, production). They are typically connected to a single GitHub repository and can be used to manage multiple services and resources across different environments.


## GitHub Release Pipelines

You can use the LaunchFlow GitHub app to automatically deploy your code and promote it between environments when you merge a pull request. See the [Deploy from GitHub](/docs/launchflow-cloud/github-deployments#setup-push-rules) guide for more information.

## List Projects

```bash
lf projects list
```

<!-- TODO improve this page -->
