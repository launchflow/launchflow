# Compute Engine Resources

Resources for [Google Cloud Compute Engine](https://cloud.google.com/products/compute). Available resources include:
- [`ComputeEngine`](https://docs.launchflow.com/reference/gcp-resources/compute-engine#compute-engine): A Compute Engine VM running a Docker Container.
- [`ComputeEnginePostgres`](https://docs.launchflow.com/reference/gcp-resources/compute-engine#compute-engine-postgres): A Postgres instance running on a VM in Google Compute Engine.
- [`ComputeEngineRedis`](https://docs.launchflow.com/reference/gcp-resources/compute-engine#compute-engine-redis): A Redis instance running on a VM in Google Compute Engine.

## Example Usage

### Create a VM running a Postgres instance

```python
from sqlalchemy import text
import launchflow as lf

postgres_compute_engine = lf.gcp.ComputeEnginePostgres("ce-postgres-mn-test-2")
engine = postgres_compute_engine.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### Create a VM running a Redis instance

```python
import launchflow as lf

redis = lf.gcp.ComputeEngineRedis("my-redis-instance")

# Set a key-value pair
client = redis.redis()
client.set("my-key", "my-value")

# Async compatible
async_client = await redis.redis_async()
await async_client.set("my-key", "my-value")
```

## ComputeEngine

A Compute Engine VM running a Docker container.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/compute/docs/).

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to a Compute Engine VM with a provided Docker image
compute_engine = lf.gcp.ComputeEngine("my-compute-engine", vm_config=lf.gcp.compute_engine.VMConfig(
    additional_outputs={"my_output": "my_value"},
    docker_cfg=lf.gcp.compute_engine.DockerConfig(
        image="my-docker-image",
        args=[],
        environment_variables=[lf.gcp.compute_engine.EnvironmentVariable("MY_ENV_VAR": "my_value")],
    ),
    firewall_cfg=lf.gcp.compute_engine.FirewallConfig(expose_ports=[80]),
))
```

### initialization

Create a Compute Engine resource.

**Args:**
- `name (str)`: The name of the resource. This must be globally unique.
- `vm_config (VMConfig)`: The configuration for the VM.
    - `additional_outputs (dict)`: Additional outputs to be returned by the resource.
    - `service_account_email (str)`: The email of the service account to use. If none a unique service account will be created. If equal to the literal "environment" the environment service account will be used
    - `docker_cfg (DockerConfig)`: The configuration for the Docker container.
        - `image (str)`: The Docker image to run.
        - `args (List[str])`: The arguments to pass to the Docker container.
        - `environment_variables (List[EnvironmentVariable])`: Environment variables to set in the Docker container.
    - `firewall_cfg (FirewallConfig)`: The configuration for the firewall rules.
        - `expose_ports (List[int])`: The ports to expose in the firewall.

### inputs

```python
ComputeEngine.inputs(environment_state: EnvironmentState) -> VMConfig
```

Get the inputs for the Compute Engine VM resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `VMConfig`: The inputs for the Compute Engine VM resource.

## ComputeEnginePostgres

A Postgres instance running on a VM in Google Compute Engine.

### Example usage
```python
from sqlalchemy import text
import launchflow as lf

postgres_compute_engine = lf.gcp.ComputeEnginePostgres("ce-postgres-mn-test-2")
engine = postgres_compute_engine.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### initialization

Create a new Compute Engine Postgres resource.

**Args:**
- `name (str)`: The name of the Postgres VM resource. This must be globally unique.
- `password (str)`: The password for the Postgres DB. If not provided, a random password will be generated.

### inputs

```python
ComputeEnginePostgres.inputs(environment_state: EnvironmentState) -> VMConfig
```

Get the inputs for the Compute Engine Postgres resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `VMConfig`: The inputs for the Compute Engine Postgres resource.

### query

```python
ComputeEnginePostgres.query(query: str)
```

Executes a SQL query on the Postgres instance running on the Compute Engine VM.

**Args:**
- `query (str)`: The SQL query to execute.

**Returns:**
- The results of the query.

**Example usage:**
```python
import launchflow as lf

postgres = lf.gcp.ComputeEnginePostgres("my-pg-db")

# Executes a query on the Postgres instance running on the Compute Engine VM
postgres.query("SELECT 1")
```

**NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.

### django\_settings

```python
ComputeEnginePostgres.django_settings()
```

Returns a Django settings dictionary for connecting to the Postgres instance running on the Compute Engine VM.

**Returns:**
- A dictionary of Django settings for connecting to the Postgres instance.

**Example usage:**
```python
import launchflow as lf

postgres = lf.gcp.ComputeEnginePostgres("my-pg-db")

# settings.py
DATABASES = {
    # Connect Django's ORM to the Postgres instance running on the Compute Engine VM
    "default": postgres.django_settings(),
}
```

### sqlalchemy\_engine\_options

```python
ComputeEnginePostgres.sqlalchemy_engine_options()
```

Returns the SQLAlchemy engine options for connecting to the Postgres instance running on the Compute Engine VM.

**Returns:**
- A dictionary of SQLAlchemy engine options for connecting to the Postgres instance.

### sqlalchemy\_async\_engine\_options

```python
async ComputeEnginePostgres.sqlalchemy_async_engine_options()
```

Returns the async SQLAlchemy engine options for connecting to the Postgres instance running on the Compute Engine VM.

**Returns:**
- A dictionary of async SQLAlchemy engine options for connecting to the Postgres instance.

### sqlalchemy\_engine

```python
ComputeEnginePostgres.sqlalchemy_engine(**engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to a Postgres instance hosted on GCP compute engine.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

**Returns:**
- The SQLAlchemy engine.

**Example usage:**
```python
import launchflow as lf
db = lf.gcp.ComputeEnginePostgres("my-pg-db")
engine = db.sqlalchemy_engine()
```

### sqlalchemy\_async\_engine

```python
async ComputeEnginePostgres.sqlalchemy_async_engine(**engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to a Postgres instance hosted on GCP compute engine.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

**Returns:**
- The async SQLAlchemy engine.

**Example usage:**
```python
import launchflow as lf
db = lf.gcp.ComputeEnginePostgres("my-pg-db")
engine = await db.sqlalchemy_async_engine()
```

## ComputeEngineRedis

A Redis instance running on a VM in Google Compute Engine.

### Example usage
```python
import launchflow as lf

redis = lf.gcp.ComputeEngineRedis("my-redis-instance")

# Set a key-value pair
client = redis.redis()
client.set("my-key", "my-value")

# Async compatible
async_client = await redis.redis_async()
await async_client.set("my-key", "my-value")
```

### initialization

Create a new Compute Engine Redis resource.

**Args:**
- `name (str)`: The name of the Redis VM resource. This must be globally unique.
- `password (str)`: The password for the Redis DB. If not provided, a random password will be generated.

### inputs

```python
ComputeEngineRedis.inputs(environment_state: EnvironmentState) -> VMConfig
```

Get the inputs for the Compute Engine Redis resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `VMConfig`: The inputs for the Compute Engine Redis resource.

### django\_settings

```python
ComputeEngineRedis.django_settings()
```

Returns a Django settings dictionary for connecting to the Redis instance running on the Compute Engine VM.

**Returns:**
- A dictionary of Django settings for connecting to the Redis instance.

**Example usage:**
```python
import launchflow as lf

redis = lf.gcp.ComputeEngineRedis("my-redis-instance")

# settings.py
CACHES = {
    # Connect Django's cache to the Redis instance running on the Compute Engine VM
    "default": redis.django_settings(),
}
```

### redis

```python
ComputeEngineRedis.redis(*, decode_responses: bool = True)
```

Get a Generic Redis Client object from the redis-py library.

**Args:**
- `decode_responses (bool)`: Whether to decode responses from the Redis server. Defaults to True.

**Returns:**
- The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.

### redis\_async

```python
async ComputeEngineRedis.redis_async(*, decode_responses: bool = True)
```

Get an Async Redis Client object from the redis-py library.

**Args:**
- `decode_responses (bool)`: Whether to decode responses from the Redis server. Defaults to True.

**Returns:**
- The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.
