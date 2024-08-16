PROJECT_HELP = "The project name to use. If not specified, we will check your local config, if not in your config it will be selected interactively."
ENVIRONMENT_HELP = "The environment name to use. If not specified, we will check your local config, if not in your config it will be selected interactively."
RUN_ENVIRONMENT_HELP = "The environment name to use or `local` to run with local versions of your generic resources."
SERVICE_HELP = "The service name to use for the operation."
SCAN_DIRECTORY_HELP = (
    "Directory to scan for resources. Defaults to the current working directory."
)
SERVICE_DEPLOY_HELP = "A list of service names to deploy. This can be specified multiple times to deploy multiple services. If not provided all services will be deployed."
SERVICE_PROMOTE_HELP = "A list of service names to promote. This can be specified multiple times to promote multiple services. If not provided all services will be promoted."
API_KEY_HELP = "API key to use for this request. If not set will fallback to your user local credentials from `lf login`"
