## APIGateway

An API Gateway

****Example usage:****
```python
import launchflow as lf

nat = lf.aws.APIGateway("my-api-gateway")
```

### initialization

TODO

### inputs

```python
APIGateway.inputs(environment_state: EnvironmentState) -> APIGatewayInputs
```

Get the inputs required for the API Gateway.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `APIGatewayInputs`: The inputs required for the API Gateway

### add\_route

```python
APIGateway.add_route(path: str) -> None
```

TODO

## APIGatewayLambdaIntegration

An API Gateway Integration

****Example usage:****
```python
import launchflow as lf

api_gateway = lf.aws.APIGateway("my-api-gateway")
function = lf.aws.LambdaFunction("my-lambda-function")
integration = lf.aws.APIGatewayLambdaIntegrationOutputs(
    "my-api-gateway-route",
    api_gateway=api_gateway,
    function=function,
)
```

### initialization

TODO

### inputs

```python
APIGatewayLambdaIntegration.inputs(environment_state: EnvironmentState) -> APIGatewayLambdaIntegrationInputs
```

Get the inputs required for the API Gateway Lambda Integration.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `APIGatewayLambdaIntegrationInputs`: The inputs required for the API Gateway Lambda Integration

## APIGatewayRoute

An API Gateway Route

****Example usage:****
```python
import launchflow as lf

api_gateway = lf.aws.APIGateway("my-api-gateway")
route = lf.aws.APIGatewayRoute("my-api-gateway-route", api_gateway=api_gateway)
```

### initialization

TODO

### inputs

```python
APIGatewayRoute.inputs(environment_state: EnvironmentState) -> APIGatewayRouteInputs
```

Get the inputs required for the API Gateway Route.

**Args:**
 - `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
 - `APIGatewayRouteInputs`: The inputs required for the API Gateway Route
