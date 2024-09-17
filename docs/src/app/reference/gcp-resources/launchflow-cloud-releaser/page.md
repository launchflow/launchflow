## LaunchFlowCloudReleaser

A resource for connecting your environment to LaunchFlow Cloud. For additional information see the documentation for the [LaunchFlow Cloud GitHub integration](https://docs.launchflow.com/docs/launchflow-cloud/github-deployments).

Connecting your environment with `lf cloud connect ${ENV_NAME}` will automatically create this resource.

### initialization

Create a new LaunchFlowCloudReleaser resource.

**Args:**
- `name`: The name of the LaunchFlowCloudReleaser resource. This must be globally unique.

### connect\_to\_launchflow

```python
async LaunchFlowCloudReleaser.connect_to_launchflow()
```

Connect the environment to LaunchFlow Cloud.
