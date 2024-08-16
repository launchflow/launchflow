## LaunchFlowCloudReleaser

A resource for connecting your environment to LaunchFlow Cloud. For additional information see the documentation for the [LaunchFlow Cloud GitHub integration](https://docs.launchflow.com/docs/launchflow-cloud/github-deployments).

Connecting your environment with `lf cloud connect ${ENV_NAME}` will automatically create this resource.

### initialization

Create a new LaunchFlowCloudReleaser resource.

### inputs

```python
LaunchFlowCloudReleaser.inputs(environment_state: EnvironmentState) -> LaunchFlowCloudReleaserInputs
```

Get the inputs for the LaunchFlowCloudReleaser resource.

**Args:**
- `environment_type` (EnvironmentType): The type of environment.

**Returns:**
- LaunchFlowCloudReleaserInputs: The inputs for the LaunchFlowCloudReleaser resource.

### connect\_to\_launchflow

```python
async LaunchFlowCloudReleaser.connect_to_launchflow()
```

Connect the environment to LaunchFlow Cloud.
