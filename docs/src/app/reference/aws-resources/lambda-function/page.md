## LambdaFunction

A Lambda function.

### Example Usage
```python
import launchflow as lf

lambda_func = lf.aws.LambdaFunction("my-lambda-function")
```

### initialization

Create a new Lambda Function.

**Args:**
- `name (str)`: The name of the Lambda Function.
- `timeout_seconds (int)`: The number of seconds before the Lambda function times out.
- `memory_size_mb (int)`: The amount of memory in MB allocated to the Lambda function.
- `package_type (Literal["Image", "Zip"])`: The type of package for the Lambda function.
- `runtime (Optional[LambdaRuntime])`: The runtime for the Lambda function.

**Raises:**
- `ValueError`: If `runtime` is `None` and `package_type` is "Zip".

## LambdaFunctionURL

A Lambda function URL.

### Example Usage
```python
import launchflow as lf

function = lf.aws.LambdaFunction("my-lambda-function")
function_url = lf.aws.LambdaFunctionURL("my-lambda-url", function=function)
```
