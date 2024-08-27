---
title: LaunchFlow YAML
nextjs:
  metadata:
    title: LaunchFlow YAML
    description: LaunchFlow YAML Schema
---

`launchflow.yaml` contains the default configuration for your project. A basic `launchflow.yaml` file looks like this:

```yaml
project: my-project
backend: lf://default
```

This yaml config tells LaunchFlow which where to store its state (lock files, deployment status, etc), and what project to use. You can update this file at any time by running `lf init` again. Be careful though -- if you switch your backend, your state won't automatically be moved (yet).
