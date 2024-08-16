# lf

CLI for interacting with LaunchFlow. Use the LaunchFlow CLI to create and manage your cloud environments and resources.

**Usage**:

```console
$ lf [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--disable-usage-statistics / --no-disable-usage-statistics`: If true no usage statistics will be collected.  [default: no-disable-usage-statistics]
* `--log-level TEXT`
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `accounts`: Commands for managing accounts in LaunchFlow
* `cloud`: Commands for interacting with LaunchFlow Cloud.
* `create`: Create any resources that are not already created.
* `deploy`: Deploy a service to a project / environment.
* `destroy`: Destroy all resources in the project / environment.
* `environments`: Interact with your LaunchFlow environments.
* `import`
* `init`: Initialize a new launchflow project.
* `login`: Login to LaunchFlow. If you haven't signup this will create a free account for you.
* `logout`: Logout of LaunchFlow.
* `projects`: Interact with your LaunchFlow projects.
* `promote`: Promote a service. This will take the image that is running in `from_environment` and promote it to a service in `to_environment`.
* `resources`: Commands for viewing resources managed by LaunchFlow
* `run`: Run a command against an environment.

Sample commands:

    lf run dev -- ./run.sh
        - Runs ./run.sh against dev environment resources.
* `secrets`: Commands for managing secrets in LaunchFlow
* `services`: Commands for viewing services managed by LaunchFlow
* `version`: Print the version of launchflow.

## lf accounts

Commands for managing accounts in LaunchFlow

**Usage**:

```console
$ lf accounts [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `get`: Get information about a specific account.
* `list`: List accounts that you have access to.

### lf accounts get

Get information about a specific account.

**Usage**:

```console
$ lf accounts get [OPTIONS] [ACCOUNT_ID]
```

**Arguments**:

* `[ACCOUNT_ID]`: [default: The account ID to fetch. Format: `account_123`]

**Options**:

* `--help`: Show this message and exit.

### lf accounts list

List accounts that you have access to.

**Usage**:

```console
$ lf accounts list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## lf cloud

Commands for interacting with LaunchFlow Cloud.

**Usage**:

```console
$ lf cloud [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `connect`: Connect an environment to LaunchFlow.

For GCP this will create a service account that will be able to deploy your services, and allow LaunchFlow Cloud to use the service account to trigger deployments.

### lf cloud connect

Connect an environment to LaunchFlow.

For GCP this will create a service account that will be able to deploy your services, and allow LaunchFlow Cloud to use the service account to trigger deployments.

**Usage**:

```console
$ lf cloud connect [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment to connect.

**Options**:

* `--help`: Show this message and exit.

## lf create

Create any resources that are not already created.

**Usage**:

```console
$ lf create [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `--resource TEXT`: Resource name to create. If none we will scan the directory for available resources. This can be specified multiple times to create multiple resources.  [default: <class 'list'>]
* `--service TEXT`: Service name to create. If none we will scan the directory for available services. This can be specified multiple times to create multiple services.  [default: <class 'list'>]
* `--scan-directory TEXT`: Directory to scan for resources. Defaults to the current working directory.  [default: .]
* `-y, --auto-approve`: Auto approve resource creation.
* `--local`: Create only local resources.
* `--launchflow-api-key TEXT`: API key to use for this request. If not set will fallback to your user local credentials from `lf login`
* `-v, --verbose`: If set all logs will be written to stdout.
* `--help`: Show this message and exit.

## lf deploy

Deploy a service to a project / environment.

**Usage**:

```console
$ lf deploy [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `--service TEXT`: A list of service names to deploy. This can be specified multiple times to deploy multiple services. If not provided all services will be deployed.  [default: <class 'list'>]
* `-y, --auto-approve`: Auto approve the deployment.
* `--skip-build / --no-skip-build`: If true the service will not be built, and the currently deployed build will be used.  [default: no-skip-build]
* `--launchflow-api-key TEXT`: API key to use for this request. If not set will fallback to your user local credentials from `lf login`
* `--scan-directory TEXT`: Directory to scan for resources. Defaults to the current working directory.  [default: .]
* `-v, --verbose`: Verbose output. Will include all options provided to your service.
* `--build-local`: Build the Docker image locally.
* `--skip-create`: Skip the Resource creation step.
* `--check-dockerfiles`: Ensure that Service Dockerfiles exist before deploying.
* `--help`: Show this message and exit.

## lf destroy

Destroy all resources in the project / environment.

**Usage**:

```console
$ lf destroy [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `--resource TEXT`: Resource name to destroy. If none we will scan the directory for available resources. This can be specified multiple times to destroy multiple resources.  [default: <class 'list'>]
* `--service TEXT`: Service name to destroy. If none we will scan the directory for available services. This can be specified multiple times to destroy multiple services.  [default: <class 'list'>]
* `--local`: Only destroy local resources.
* `-y, --auto-approve`: Auto approve resource destruction.
* `-v, --verbose`: If set all logs will be written to stdout.
* `--launchflow-api-key TEXT`: API key to use for this request. If not set will fallback to your user local credentials from `lf login`
* `--help`: Show this message and exit.

## lf environments

Interact with your LaunchFlow environments.

**Usage**:

```console
$ lf environments [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `create`: Create a new environment in the current project.
* `delete`: Delete an environment.
* `get`: Get information about a specific environment.
* `list`: List all environments in the current directory's project.
* `unlock`: Force unlock an environment.

### lf environments create

Create a new environment in the current project.

**Usage**:

```console
$ lf environments create [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: The environment name.

**Options**:

* `--env-type [unknown|development|production]`: The environment type (`development` or `production`).
* `--cloud-provider [unknown|gcp|aws]`: The cloud provider.
* `--gcp-project-id TEXT`: The GCP project ID to import.
* `--gcp-organization-name TEXT`: The GCP organization name (organization/XXXXXX) to place newly create GCP projects in. If not provided you will be prompted to select an organization.
* `--gcp-service-account-email TEXT`: The GCP service account email to import for the environment.
* `-y, --auto-approve`: Auto approve environment creation.
* `--help`: Show this message and exit.

### lf environments delete

Delete an environment.

**Usage**:

```console
$ lf environments delete [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: The environment name.

**Options**:

* `--detach / --no-detach`: If true we will not clean up any of the cloud resources associated with the environment and will simply delete the record from LaunchFlow.  [default: no-detach]
* `-y, --auto-approve`: Auto approve environment deletion.
* `-p, --project TEXT`: The project name. If not provided, the current project is used.
* `--help`: Show this message and exit.

### lf environments get

Get information about a specific environment.

**Usage**:

```console
$ lf environments get [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: The environment name.

**Options**:

* `-f, --format [default|yaml]`: Output format  [default: default]
* `-e, --expand`: List resources and services in the environment
* `--help`: Show this message and exit.

### lf environments list

List all environments in the current directory's project.

**Usage**:

```console
$ lf environments list [OPTIONS]
```

**Options**:

* `-f, --format [default|yaml]`: Output format  [default: default]
* `-e, --expand`: List resources and services in the environments
* `-p, --project TEXT`: The project name. If not provided, the current project is used.
* `--help`: Show this message and exit.

### lf environments unlock

Force unlock an environment.

**Usage**:

```console
$ lf environments unlock [OPTIONS] NAME
```

**Arguments**:

* `NAME`: The environment to unlock.  [required]

**Options**:

* `-y, --auto-approve`: Auto approve environment force unlock.
* `--include-services`: Include services in the unlock.
* `--include-resources`: Include resources in the unlock.
* `--help`: Show this message and exit.

## lf import

**Usage**:

```console
$ lf import [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `--resource TEXT`: Resource name to import. If none we will scan the directory for available resources.
* `--scan-directory TEXT`: Directory to scan for resources. Defaults to the current working directory.  [default: .]
* `--help`: Show this message and exit.

## lf init

Initialize a new launchflow project.

**Usage**:

```console
$ lf init [OPTIONS]
```

**Options**:

* `-b, --backend [local|gcs|lf]`: The backend to use for the project.
* `--help`: Show this message and exit.

## lf login

Login to LaunchFlow. If you haven't signup this will create a free account for you.

**Usage**:

```console
$ lf login [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## lf logout

Logout of LaunchFlow.

**Usage**:

```console
$ lf logout [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## lf projects

Interact with your LaunchFlow projects.

**Usage**:

```console
$ lf projects [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `create`: Create a new project in your account.
* `delete`: Delete a project.
* `list`: Lists all current projects in your account.

### lf projects create

Create a new project in your account.

**Usage**:

```console
$ lf projects create [OPTIONS] [PROJECT]
```

**Arguments**:

* `[PROJECT]`: The project name.

**Options**:

* `-y, --auto-approve`: Auto approve project creation.
* `--help`: Show this message and exit.

### lf projects delete

Delete a project.

**Usage**:

```console
$ lf projects delete [OPTIONS] NAME
```

**Arguments**:

* `NAME`: The project name.  [required]

**Options**:

* `-y, --auto-approve`: Auto approve project deletion.
* `--help`: Show this message and exit.

### lf projects list

Lists all current projects in your account.

**Usage**:

```console
$ lf projects list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## lf promote

Promote a service. This will take the image that is running in `from_environment` and promote it to a service in `to_environment`.

**Usage**:

```console
$ lf promote [OPTIONS] FROM_ENVIRONMENT TO_ENVIRONMENT
```

**Arguments**:

* `FROM_ENVIRONMENT`: The environment to promote from.  [required]
* `TO_ENVIRONMENT`: The environment to promote to  [required]

**Options**:

* `--service TEXT`: A list of service names to promote. This can be specified multiple times to promote multiple services. If not provided all services will be promoted.  [default: <class 'list'>]
* `-y, --auto-approve`: Auto approve the deployment.
* `--launchflow-api-key TEXT`: API key to use for this request. If not set will fallback to your user local credentials from `lf login`
* `--promote-local / --no-promote-local`: Promote the service locally. If true this will move the docker image to the new environment locally instead of on Cloud Build or Code Build.  [default: no-promote-local]
* `--scan-directory TEXT`: Directory to scan for resources. Defaults to the current working directory.  [default: .]
* `-v, --verbose`: Verbose output. Will include all options provided to your service.
* `--help`: Show this message and exit.

## lf resources

Commands for viewing resources managed by LaunchFlow

**Usage**:

```console
$ lf resources [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List all resources in a project/environment.
* `unlock`: Force unlock a resource.

### lf resources list

List all resources in a project/environment.

**Usage**:

```console
$ lf resources list [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `-f, --format [default|yaml]`: Output format  [default: default]
* `--help`: Show this message and exit.

### lf resources unlock

Force unlock a resource.

**Usage**:

```console
$ lf resources unlock [OPTIONS] ENVIRONMENT RESOURCE
```

**Arguments**:

* `ENVIRONMENT`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.  [required]
* `RESOURCE`: The resource to unlock.  [required]

**Options**:

* `-y, --auto-approve`: Auto approve environment force unlock.
* `--help`: Show this message and exit.

## lf run

Run a command against an environment.

Sample commands:

    lf run dev -- ./run.sh
        - Runs ./run.sh against dev environment resources.

**Usage**:

```console
$ lf run [OPTIONS] ENVIRONMENT [ARGS]...
```

**Arguments**:

* `ENVIRONMENT`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.  [required]
* `[ARGS]...`: Additional command to run

**Options**:

* `--scan-directory TEXT`: Directory to scan for resources. Defaults to the current working directory.  [default: .]
* `--disable-run-cache`: Disable the run cache, Resource outputs will always be fetched.
* `--launchflow-api-key TEXT`: API key to use for this request. If not set will fallback to your user local credentials from `lf login`
* `--help`: Show this message and exit.

## lf secrets

Commands for managing secrets in LaunchFlow

**Usage**:

```console
$ lf secrets [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `set`: Set the value of a secret managed by LaunchFlow.

### lf secrets set

Set the value of a secret managed by LaunchFlow.

**Usage**:

```console
$ lf secrets set [OPTIONS] RESOURCE_NAME SECRET_VALUE
```

**Arguments**:

* `RESOURCE_NAME`: Resource to fetch information for.  [required]
* `SECRET_VALUE`: The value to set for the secret.  [required]

**Options**:

* `--environment TEXT`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.  [required]
* `--help`: Show this message and exit.

## lf services

Commands for viewing services managed by LaunchFlow

**Usage**:

```console
$ lf services [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List all services in a project/environment.
* `unlock`: Force unlock a service.

### lf services list

List all services in a project/environment.

**Usage**:

```console
$ lf services list [OPTIONS] [ENVIRONMENT]
```

**Arguments**:

* `[ENVIRONMENT]`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.

**Options**:

* `-f, --format [default|yaml]`: Output format  [default: default]
* `--help`: Show this message and exit.

### lf services unlock

Force unlock a service.

**Usage**:

```console
$ lf services unlock [OPTIONS] ENVIRONMENT SERVICE
```

**Arguments**:

* `ENVIRONMENT`: The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively.  [required]
* `SERVICE`: The service to unlock.  [required]

**Options**:

* `-y, --auto-approve`: Auto approve environment force unlock.
* `--help`: Show this message and exit.

## lf version

Print the version of launchflow.

**Usage**:

```console
$ lf version [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
