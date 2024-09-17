# EC2 Resources

Resources for [AWS Elastic Container Service](https://aws.amazon.com/ecs/). Available resources include:
- [`EC2`](https://docs.launchflow.com/reference/aws-resources/ec2#ec-2): A Compute Engine VM running a Docker Container.
- [`EC2Postgres`](https://docs.launchflow.com/reference/aws-resources/ec2#ec-2-postgres): A Postgres instance running on a VM in AWS EC2.
- [`EC2Redis`](https://docs.launchflow.com/reference/aws-resources/ec2#ec--redis): A Redis instance running on a VM on a VM in AWS EC2.

## Example Usage

### Create a VM running a Postgres instance
```python
from sqlalchemy import text
import launchflow as lf

postgres = lf.aws.EC2Postgres("my-postgres-db")
engine = postgres.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### Create a VM running a Redis instance

```python
import launchflow as lf

redis_vm = lf.aws.EC2Redis("my-redis-instance")

# Set a key-value pair
client = redis_vm.redis()
client.set("my-key", "my-value")

# Async compatible
async_client = await redis_vm.redis_async()
await async_client.set("my-key", "my-value")
```

## EC2

An EC2 instance running a Docker container.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://docs.aws.amazon.com/ec2/).

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to an ECS VM with a provided Docker image
ec2_instance = lf.aws.EC2("my-instance", vm_config=lf.aws.ec2.VMConfig(
    additional_outputs={"my_output": "my_value"},
    docker_cfg=lf.aws.ec2.DockerConfig(
        image="my-docker-image",
        args=[],
        environment_variables={"MY_ENV_VAR": "my_value"},
    ),
    firewall_cfg=lf.aws.ec2.FirewallConfig(expose_ports=[80]),
))
```

### initialization

Create a new EC2 resource.

**Args:**
- `name (str)`: The name of the resource. This must be globally unique.
- `vm_config (VMConfig)`: The configuration for the VM.
    - `instance_type (str)`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
    - `additional_outputs (dict)`: Additional outputs to be returned by the resource.
    - `docker_cfg (DockerConfig)`: The configuration for the Docker container.
        - `image (str)`: The Docker image to run.
        - `args (List[str])`: The arguments to pass to the Docker container.
        - `environment_variables (dict)`: Environment variables to set in the Docker container.
    - `firewall_cfg (FirewallConfig)`: The configuration for the firewall rules.
        - `expose_ports (List[int])`: The ports to expose in the firewall.
    - `disk_size_gb (int)`: The size of the disk in GB. Defaults to 8.

### ssh

```python
EC2.ssh()
```

Open an SSH session to the VM.

**Example usage**:
```python
import launchflow as lf

vm = lf.aws.EC2("my-vm")
vm.ssh()
```

## EC2Postgres

An EC2 instance running Postgres on Docker.

### Example usage
```python
from sqlalchemy import text
import launchflow as lf

postgres = lf.aws.EC2Postgres("my-postgres-db")
engine = postgres.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### initialization

Create a new EC2Postgres resource.

**Args:**
- `name (str)`: The name of the Postgres VM resource. This must be globally unique.
- `password (Optional[str])`: The password for the Postgres DB. If not provided, a random password will be generated.
- `instance_type (Optional[str)`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
- `disk_size_gb (Optional[str])`: The size of the disk in GB. Defaults to 8.

### query

```python
EC2Postgres.query(query: str)
```

Executes a SQL query on the Postgres instance running on the EC2 VM.

**Args:**
- `query`: The SQL query to execute.

**Returns:**
- The result of the query.

**Example usage:**
```python
import launchflow as lf

postgres = lf.aws.EC2Postgres("my-pg-db")

# Executes a query on the Postgres instance running on the EC2 VM
postgres.query("SELECT 1")
```

**NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.

### django\_settings

```python
EC2Postgres.django_settings()
```

Returns a Django settings dictionary for connecting to the Postgres instance running on EC2.

**Returns:**
- A dictionary of Django settings for connecting to the Postgres instance.

**Example usage:**
```python
import launchflow as lf

postgres = lf.aws.EC2Postgres("my-pg-db")

# settings.py
DATABASES = {
    # Connect Django's ORM to the Postgres instance running on EC2
    "default": postgres.django_settings(),
}
```

### sqlalchemy\_engine\_options

```python
EC2Postgres.sqlalchemy_engine_options()
```

Returns SQLAlchemy engine options for connecting to the Postgres instance running on EC2.

**Returns:**
- A dictionary of SQLAlchemy engine options.

### sqlalchemy\_async\_engine\_options

```python
async EC2Postgres.sqlalchemy_async_engine_options()
```

Returns async SQLAlchemy engine options for connecting to the Postgres instance running on EC2.

**Returns:**
- A dictionary of async SQLAlchemy engine options.

### sqlalchemy\_engine

```python
EC2Postgres.sqlalchemy_engine(**engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to a postgres instance hosted on EC2.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

**Returns:**
- A SQLAlchemy engine.

### sqlalchemy\_async\_engine

```python
async EC2Postgres.sqlalchemy_async_engine(**engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to a postgres instance hosted on EC2.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

**Returns:**
- An async SQLAlchemy engine.

## EC2Redis

An EC2 instance running Redis on Docker.

### Example usage
```python
import launchflow as lf

redis_vm = lf.aws.EC2Redis("my-redis-instance")

# Set a key-value pair
client = redis_vm.redis()
client.set("my-key", "my-value")

# Async compatible
async_client = await redis_vm.redis_async()
await async_client.set("my-key", "my-value")
```

### initialization

Create a new EC2Redis resource.

**Args:**
- `name (str)`: The name of the Redis VM resource. This must be globally unique.
- `password (Optional[str])`: The password for the Redis DB. If not provided, a random password will be generated.
- `instance_type (Optional[str])`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
- `disk_size_gb (Optional[int])`: The size of the disk in GB. Defaults to 8.

### django\_settings

```python
EC2Redis.django_settings()
```

Returns a Django settings dictionary for connecting to the Redis instance running on EC2.

**Returns:**
- A dictionary of Django settings for connecting to the Redis instance.

**Example usage:**
```python
import launchflow as lf

redis_vm = lf.aws.EC2Redis("my-redis-vm")

# settings.py
CACHES = {
    # Connect Django's cache backend to the Redis instance running on EC2
    "default": redis_vm.django_settings(),
}
```

### redis

```python
EC2Redis.redis(*, decode_responses: bool = True)
```

Get a Generic Redis Client object from the redis-py library.

**Args:**
- `decode_responses` (bool): Whether to decode responses from the Redis server. Defaults to True.

**Returns:**
- The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.

**Example usage:**
```python
import launchflow as lf

redis_vm = lf.aws.EC2Redis("my-redis-instance")
client = redis_vm.redis()
client.set("my-key", "my-value")
```

### redis\_async

```python
async EC2Redis.redis_async(*, decode_responses: bool = True)
```

Get an Async Redis Client object from the redis-py library.

**Args:**
- `decode_responses` (bool): Whether to decode responses from the Redis server. Defaults to True.

**Returns:**
- The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.

**Example usage:**
```python
import launchflow as lf

redis_vm = lf.aws.EC2Redis("my-redis-instance")
async_client = await redis_vm.redis_async()
await async_client.set("my-key", "my-value")
```

## EC2SimpleServer

An EC2 instance running a simple server on Docker.

### initialization

Create a new EC2SimpleServer resource.

**Args:**
- `name` (str): The name of the Redis VM resource. This must be globally unique.
- `instance_type`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
- `disk_size_gb`: The size of the disk in GB. Defaults to 8.

## EC2MySQL

An EC2 instance running MySQL on Docker.

### Example usage
```python
from sqlalchemy import text
import launchflow as lf

mysql = lf.aws.EC2MySQL("my-mysql-db")
engine = mysql.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### initialization

Create a new EC2MySQL resource.

**Args:**
- `name (str)`: The name of the MySQL VM resource. This must be globally unique.
- `password (Optional[str])`: The password for the MySQL DB. If not provided, a random password will be generated.
- `instance_type (Optional[str])`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
- `disk_size_gb (Optional[str])`: The size of the disk in GB. Defaults to 8.

### query

```python
EC2MySQL.query(query: str)
```

Executes a SQL query on the MySQL instance running on the EC2 VM.

**Args:**
- `query`: The SQL query to execute.

**Returns:**
- The result of the query.

**Example usage:**
```python
import launchflow as lf

mysql = lf.aws.EC2MySQL("my-mysql-db")

# Executes a query on the MySQL instance running on the EC2 VM
mysql.query("SELECT 1")
```

**NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.

### django\_settings

```python
EC2MySQL.django_settings()
```

Returns a Django settings dictionary for connecting to the MySQL instance running on EC2.

**Returns:**
- A dictionary of Django settings for connecting to the MySQL instance.

**Example usage:**
```python
import launchflow as lf

mysql = lf.aws.EC2MySQL("my-mysql-db")

# settings.py
DATABASES = {
    # Connect Django's ORM to the MySQL instance running on EC2
    "default": mysql.django_settings(),
}
```

### sqlalchemy\_engine\_options

```python
EC2MySQL.sqlalchemy_engine_options()
```

Returns SQLAlchemy engine options for connecting to the MySQL instance running on EC2.

**Returns:**
- A dictionary of SQLAlchemy engine options.

### sqlalchemy\_async\_engine\_options

```python
async EC2MySQL.sqlalchemy_async_engine_options()
```

Returns async SQLAlchemy engine options for connecting to the MySQL instance running on EC2.

**Returns:**
- A dictionary of async SQLAlchemy engine options.

### sqlalchemy\_engine

```python
EC2MySQL.sqlalchemy_engine(**engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to a MySQL instance hosted on EC2.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

**Returns:**
- A SQLAlchemy engine.

### sqlalchemy\_async\_engine

```python
async EC2MySQL.sqlalchemy_async_engine(**engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to a MySQL instance hosted on EC2.

**Args:**
- `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

**Returns:**
- An async SQLAlchemy engine.
