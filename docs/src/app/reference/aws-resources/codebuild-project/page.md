## CodeBuildProject

A resource for creating a CodeBuild project.

### Example Usage
```python
import launchflow as lf

codebuild_environment = lf.aws.codebuild_project.Environment(...)
codebuild_source = lf.aws.codebuild_project.Source(...)
codebuild_project = lf.aws.CodeBuildProject("my-codebuild-project", environment=)
```

### initialization

Create a new CodeBuildProject resource.

**Args:**
- `name (str)`: The name of the CodeBuildProject resource. This must be globally unique.
- `environment (Environment)`: The CodeBuild project environment to use.
- `build_source (Source)`: The CodeBuild project source to use.
- `logs_config (Optional[LogsConfig])`: The logs configuration for the CodeBuild project. Defaults to None.
- `cache (Optional[Cache])`: The cache configuration for the CodeBuild project. Defaults to None.
- `build_timeout_minutes: int`: The build timeout for the CodeBuild project. Default to 30 minutes.
