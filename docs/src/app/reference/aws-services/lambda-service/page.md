## LambdaService

A service hosted on AWS Lambda.

Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information, see [the official documentation](https://aws.amazon.com/lambda/).

### Example Usage

#### Basic Usage

```python
import launchflow as lf

# This points to the `handler` function in the `app` module
api = lf.aws.LambdaService("my-api", handler="app.handler")
```

#### Custom Timeout and Memory Size

```python
import launchflow as lf

service = lf.aws.LambdaService(
    "my-lambda-service",
    handler="app.handler",
    timeout_seconds=30,
    memory_size_mb=512
)
```

#### Environment Variables

```python
import launchflow as lf

service = lf.aws.LambdaService(
    "my-lambda-service",
    handler="app.handler",
    env={"STAGE": "prod", "LOG_LEVEL": "debug"}
)
```

#### Custom URL Configuration

```python
import launchflow as lf

api_gateway = lf.aws.APIGateway("my-api-gateway")
# The functions will share the same API Gateway
read_api = lf.aws.LambdaService(
    "my-read-api",
    handler="app.list_users",
    url=lf.aws.APIGatewayURL(api_gateway=api_gateway, route_key="GET /users")
)
write_api = lf.aws.LambdaService(
    "my-write-api",
    handler="app.create_user",
    url=lf.aws.APIGatewayURL(api_gateway=api_gateway, route_key="POST /users")
)
```

### initialization

Create a new Lambda Service.

**Args:**
- `name (str)`: The name of the service.
- `handler (Union[str, Callable])`: The entry point for the Lambda function. If a callable is passed, it is converted to the proper handler string.
- `timeout_seconds (int)`: The timeout in seconds for the Lambda function. Defaults to 10 seconds.
- `memory_size_mb (int)`: The memory size for the Lambda function in MB. Defaults to 256 MB.
- `env (Optional[Dict[str, str]])`: Optional environment variables for the Lambda function.
- `url (Union[LambdaURL, APIGatewayURL])`: Optional URL configuration, defaults to a public Lambda URL.
- `runtime (Union[LambdaRuntime, PythonRuntime, DockerRuntime])`: The runtime environment for the Lambda function. Defaults to Python runtime.
- `domain (Optional[str])`: Optional custom domain. Currently unsupported, will raise an exception if provided.
- `build_directory (str)`: The directory to build the Lambda function from. Defaults to the current directory.
- `build_ignore (List[str])`: A list of files or directories to ignore during the build process. Defaults to an empty list.
