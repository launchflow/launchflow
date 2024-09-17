"""
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

"""

# Handling imports and missing dependencies
try:
    import redis
except ImportError:
    redis = None  # type: ignore
try:
    import asyncpg  # type: ignore
except ImportError:
    asyncpg = None

try:
    import pg8000  # type: ignore
except ImportError:
    pg8000 = None

try:
    import psycopg2  # type: ignore
except ImportError:
    psycopg2 = None

try:
    from sqlalchemy.ext.asyncio import create_async_engine
except ImportError:
    async_sessionmaker = None
    create_async_engine = None  # type: ignore

try:
    from sqlalchemy import create_engine, text
except ImportError:
    text = None  # type: ignore
    create_engine = None  # type: ignore
    DeclarativeBase = None
    sessionmaker = None


try:
    import pymysql  # type: ignore
except ImportError:
    pymysql = None

try:
    import aiomysql
except ImportError:
    aiomysql = None


import dataclasses
import os
import subprocess
from typing import Any, Dict, List, Optional

import launchflow as lf
from launchflow import exceptions
from launchflow.aws.resource import AWSResource, T
from launchflow.generic_clients import RedisClient
from launchflow.models.enums import EnvironmentType, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Inputs, Outputs
from launchflow.resource import ResourceInputs
from launchflow.utils import generate_random_password


def _check_redis_installs():
    if redis is None:
        raise ImportError(
            "redis library is not installed. Please install it with `pip install redis`."
        )


@dataclasses.dataclass
class EC2BaseOutputs(Outputs):
    private_key: str
    public_ip: str
    private_ip: str
    ports: List[int]
    additional_outputs: Any


@dataclasses.dataclass
class EC2RedisAdditionalOutputs(Outputs):
    password: str
    redis_port: str


@dataclasses.dataclass
class EC2RedisOutputs(EC2BaseOutputs):
    additional_outputs: EC2RedisAdditionalOutputs


@dataclasses.dataclass
class EC2PostgresAdditionalOutputs(Outputs):
    password: str
    postgres_port: str


@dataclasses.dataclass
class EC2PostgresOutputs(EC2BaseOutputs):
    additional_outputs: EC2PostgresAdditionalOutputs


@dataclasses.dataclass
class EC2MySQLAdditionalOutputs(Outputs):
    password: str
    mysql_port: str


@dataclasses.dataclass
class EC2MySQLOutputs(EC2BaseOutputs):
    additional_outputs: EC2MySQLAdditionalOutputs


@dataclasses.dataclass
class DockerConfig(Inputs):
    image: str
    args: List[str]
    environment_variables: Dict[str, str]


@dataclasses.dataclass
class FirewallConfig(Inputs):
    expose_ports: List[int]


@dataclasses.dataclass
class VMConfig(ResourceInputs):
    additional_outputs: Dict[str, str]
    docker_cfg: DockerConfig
    instance_type: Optional[str] = None
    firewall_cfg: Optional[FirewallConfig] = None
    disk_size_gb: Optional[int] = 8
    associate_public_ip_address: Optional[bool] = True
    publicly_accessible: Optional[bool] = True


class EC2(AWSResource[T]):
    """An EC2 instance running a Docker container.

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
    """

    product = ResourceProduct.AWS_EC2.value

    def __init__(self, name: str, vm_config: Optional[VMConfig]) -> None:
        """Create a new EC2 resource.

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
        """
        super().__init__(
            name=name,
            resource_id=f"{name}-{lf.project}-{lf.environment}",
        )
        self.vm_config = vm_config

    def inputs(self, environment_state: EnvironmentState) -> VMConfig:
        if self.vm_config is None:
            raise ValueError("vm_config is required")
        if self.vm_config.instance_type is not None:
            return self.vm_config
        if environment_state.environment_type == EnvironmentType.PRODUCTION:
            instance_type = "t3.medium"
        else:
            instance_type = "t3.micro"
        return dataclasses.replace(self.vm_config, instance_type=instance_type)

    def ssh(self):
        """Open an SSH session to the VM.

        **Example usage**:
        ```python
        import launchflow as lf

        vm = lf.aws.EC2("my-vm")
        vm.ssh()
        ```
        """

        connection_info = self.outputs()
        # Path to the temporary private key file
        key_path = f"/tmp/{self.name}_private_key.pem"

        try:
            # Write the private key to a temporary file
            with open(key_path, "w") as f:
                f.write(connection_info.private_key)

            # Make the file read-only for the user
            os.chmod(key_path, 0o400)

            # Build the SSH command
            command = f"ssh -i {key_path} ec2-user@{connection_info.public_ip}"
            print("Executing SSH command. Please wait...")

            # Execute the SSH command. This will drop the user into the SSH session.
            subprocess.run(command, shell=True)

        finally:
            # Ensure the temporary file is deleted after the SSH session ends
            if os.path.exists(key_path):
                os.remove(key_path)
                print("Temporary private key file deleted.")

    @staticmethod
    def _get_host(outputs: EC2BaseOutputs):
        if lf.is_deployment():
            return outputs.private_ip
        return outputs.public_ip


class EC2Postgres(EC2[EC2PostgresOutputs]):
    """An EC2 instance running Postgres on Docker.

    ### Example usage
    ```python
    from sqlalchemy import text
    import launchflow as lf

    postgres = lf.aws.EC2Postgres("my-postgres-db")
    engine = postgres.sqlalchemy_engine()

    with engine.connect() as connection:
        print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
    ```
    """

    def __init__(
        self,
        name: str,
        *,
        password: Optional[str] = None,
        instance_type: Optional[str] = None,
        disk_size_gb: int = 8,
    ) -> None:
        """Create a new EC2Postgres resource.

        **Args:**
        - `name (str)`: The name of the Postgres VM resource. This must be globally unique.
        - `password (Optional[str])`: The password for the Postgres DB. If not provided, a random password will be generated.
        - `instance_type (Optional[str)`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
        - `disk_size_gb (Optional[str])`: The size of the disk in GB. Defaults to 8.
        """
        super().__init__(name=name, vm_config=None)
        self.password = password
        self.instance_type = instance_type
        self.disk_size_gb = disk_size_gb

    def inputs(self, environment_state: EnvironmentState):
        if self.password is None:
            try:
                # Attempt to see if the resource exists yet
                self.password = self.outputs().additional_outputs.password
            except exceptions.ResourceOutputsNotFound:
                self.password = generate_random_password()

        if environment_state.environment_type == EnvironmentType.PRODUCTION:
            publicly_accessible = False
        else:
            publicly_accessible = True

        self.vm_config = VMConfig(
            resource_id=self.resource_id,
            additional_outputs={"postgres_port": "5432", "password": self.password},
            docker_cfg=DockerConfig(
                image="postgres:latest",
                args=[],
                environment_variables={"POSTGRES_PASSWORD": self.password},
            ),
            instance_type=self.instance_type,
            disk_size_gb=self.disk_size_gb,
            firewall_cfg=FirewallConfig(expose_ports=[5432]),
            associate_public_ip_address=True,
            publicly_accessible=publicly_accessible,
        )
        return super().inputs(environment_state)

    def query(self, query: str):
        """Executes a SQL query on the Postgres instance running on the EC2 VM.

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
        """
        engine = self.sqlalchemy_engine()
        with engine.connect() as connection:
            result = connection.execute(text(query))
            connection.commit()
            if result.returns_rows:
                return result.fetchall()

    def django_settings(self):
        """Returns a Django settings dictionary for connecting to the Postgres instance running on EC2.

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
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Please install it with `pip install psycopg2`."
            )

        connection_info = self.outputs()
        return {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "postgres",
            "USER": "postgres",
            "PASSWORD": connection_info.additional_outputs.password,
            "HOST": self._get_host(connection_info),
            "PORT": connection_info.additional_outputs.postgres_port,
        }

    def sqlalchemy_engine_options(self):
        """Returns SQLAlchemy engine options for connecting to the Postgres instance running on EC2.

        **Returns:**
        - A dictionary of SQLAlchemy engine options.
        """
        if pg8000 is None:
            raise ImportError(
                "pg8000 is not installed. Please install it with `pip install pg8000`."
            )

        connection_info = self.outputs()
        host = self._get_host(connection_info)
        return {
            "url": f"postgresql+pg8000://postgres:{connection_info.additional_outputs.password}@{host}:{connection_info.additional_outputs.postgres_port}/postgres",
        }

    async def sqlalchemy_async_engine_options(self):
        """Returns async SQLAlchemy engine options for connecting to the Postgres instance running on EC2.

        **Returns:**
        - A dictionary of async SQLAlchemy engine options.
        """
        if asyncpg is None:
            raise ImportError(
                "asyncpg is not installed. Please install it with `pip install asyncpg`."
            )

        connection_info = await self.outputs_async()
        host = self._get_host(connection_info)
        return {
            "url": f"postgresql+asyncpg://postgres:{connection_info.additional_outputs.password}@{host}:{connection_info.additional_outputs.postgres_port}/postgres"
        }

    def sqlalchemy_engine(self, **engine_kwargs):
        """Returns a SQLAlchemy engine for connecting to a postgres instance hosted on EC2.

        **Args:**
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - A SQLAlchemy engine.
        """
        if create_engine is None:
            raise ImportError(
                "SQLAlchemy is not installed. Please install it with "
                "`pip install sqlalchemy`."
            )

        engine_options = self.sqlalchemy_engine_options()
        engine_options.update(engine_kwargs)

        return create_engine(**engine_options)

    async def sqlalchemy_async_engine(self, **engine_kwargs):
        """Returns an async SQLAlchemy engine for connecting to a postgres instance hosted on EC2.

        **Args:**
        - `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

        **Returns:**
        - An async SQLAlchemy engine.
        """
        if create_async_engine is None:
            raise ImportError(
                "SQLAlchemy asyncio extension is not installed. "
                "Please install it with `pip install sqlalchemy[asyncio]`."
            )

        engine_options = await self.sqlalchemy_async_engine_options()
        engine_options.update(engine_kwargs)

        return create_async_engine(**engine_options)


class EC2Redis(EC2[EC2RedisOutputs], RedisClient):
    """An EC2 instance running Redis on Docker.

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
    """

    def __init__(
        self,
        name: str,
        *,
        password: Optional[str] = None,
        instance_type: Optional[str] = None,
        disk_size_gb: int = 8,
    ) -> None:
        """Create a new EC2Redis resource.

        **Args:**
        - `name (str)`: The name of the Redis VM resource. This must be globally unique.
        - `password (Optional[str])`: The password for the Redis DB. If not provided, a random password will be generated.
        - `instance_type (Optional[str])`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
        - `disk_size_gb (Optional[int])`: The size of the disk in GB. Defaults to 8.
        """
        super().__init__(name=name, vm_config=None)
        self.password = password
        self.instance_type = instance_type
        self.disk_size_gb = disk_size_gb
        self._async_pool = None
        self._sync_client = None

    def inputs(self, environment_state: EnvironmentState) -> VMConfig:
        if self.password is None:
            try:
                # Attempt to see if the resource exists yet
                self.password = self.outputs().additional_outputs.password
            except exceptions.ResourceOutputsNotFound:
                self.password = generate_random_password()

        if environment_state.environment_type == EnvironmentType.PRODUCTION:
            publicly_accessible = False
        else:
            publicly_accessible = True

        self.vm_config = VMConfig(
            resource_id=self.resource_id,
            additional_outputs={"redis_port": "6379", "password": self.password},
            docker_cfg=DockerConfig(
                image="redis:latest",
                args=f"redis-server --appendonly yes --requirepass {self.password}".split(),
                environment_variables={},
            ),
            instance_type=self.instance_type,
            disk_size_gb=self.disk_size_gb,
            firewall_cfg=FirewallConfig(expose_ports=[6379]),
            associate_public_ip_address=True,
            publicly_accessible=publicly_accessible,
        )
        return super().inputs(environment_state)

    def django_settings(self):
        """Returns a Django settings dictionary for connecting to the Redis instance running on EC2.

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
        """
        connection_info = self.outputs()
        host = self._get_host(connection_info)
        return {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://default:{connection_info.additional_outputs.password}@{host}:{connection_info.additional_outputs.redis_port}",
        }

    def redis(self, *, decode_responses: bool = True):
        """Get a Generic Redis Client object from the redis-py library.

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
        """
        _check_redis_installs()
        connection_info = self.outputs()
        if self._sync_client is None:
            self._sync_client = redis.Redis(  # type: ignore
                host=self._get_host(connection_info),
                port=int(connection_info.additional_outputs.redis_port),
                password=connection_info.additional_outputs.password,
                decode_responses=decode_responses,
            )
        return self._sync_client

    async def redis_async(self, *, decode_responses: bool = True):
        """Get an Async Redis Client object from the redis-py library.

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
        """
        _check_redis_installs()
        connection_info = await self.outputs_async()
        host = self._get_host(connection_info)
        if self._async_pool is None:
            self._async_pool = await redis.asyncio.from_url(  # type: ignore
                f"redis://{host}:{connection_info.additional_outputs.redis_port}",
                password=connection_info.additional_outputs.password,
                decode_responses=decode_responses,
            )
        return self._async_pool


class EC2SimpleServer(EC2[EC2BaseOutputs]):
    """An EC2 instance running a simple server on Docker."""

    def __init__(
        self,
        name: str,
        *,
        instance_type: Optional[str] = None,
        disk_size_gb: int = 8,
    ) -> None:
        """Create a new EC2SimpleServer resource.

        **Args:**
        - `name` (str): The name of the Redis VM resource. This must be globally unique.
        - `instance_type`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
        - `disk_size_gb`: The size of the disk in GB. Defaults to 8.
        """
        super().__init__(name=name, vm_config=None)
        self.instance_type = instance_type
        self.disk_size_gb = disk_size_gb

    def inputs(self, environment_state: EnvironmentState) -> VMConfig:
        if environment_state.environment_type == EnvironmentType.PRODUCTION:
            publicly_accessible = False
        else:
            publicly_accessible = True

        self.vm_config = VMConfig(
            resource_id=self.resource_id,
            additional_outputs={"httpd_port": "80"},
            docker_cfg=DockerConfig(
                image="httpd:2.4",
                args=[],
                environment_variables={},
            ),
            instance_type=self.instance_type,
            disk_size_gb=self.disk_size_gb,
            firewall_cfg=FirewallConfig(expose_ports=[80]),
            associate_public_ip_address=True,
            publicly_accessible=publicly_accessible,
        )
        return super().inputs(environment_state)


class EC2MySQL(EC2[EC2MySQLOutputs]):
    """An EC2 instance running MySQL on Docker.

    ### Example usage
    ```python
    from sqlalchemy import text
    import launchflow as lf

    mysql = lf.aws.EC2MySQL("my-mysql-db")
    engine = mysql.sqlalchemy_engine()

    with engine.connect() as connection:
        print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
    ```
    """

    def __init__(
        self,
        name: str,
        *,
        password: Optional[str] = None,
        instance_type: Optional[str] = None,
        disk_size_gb: int = 8,
    ) -> None:
        """Create a new EC2MySQL resource.

        **Args:**
        - `name (str)`: The name of the MySQL VM resource. This must be globally unique.
        - `password (Optional[str])`: The password for the MySQL DB. If not provided, a random password will be generated.
        - `instance_type (Optional[str])`: The type of machine to use. Defaults to `t3.micro` for development environments and `t3.medium` for production environments.
        - `disk_size_gb (Optional[str])`: The size of the disk in GB. Defaults to 8.
        """
        super().__init__(name=name, vm_config=None)
        self.password = password
        self.instance_type = instance_type
        self.disk_size_gb = disk_size_gb

    def inputs(self, environment_state: EnvironmentState):
        if self.password is None:
            try:
                # Attempt to see if the resource exists yet
                self.password = self.outputs().additional_outputs.password
            except exceptions.ResourceOutputsNotFound:
                self.password = generate_random_password()

        if environment_state.environment_type == EnvironmentType.PRODUCTION:
            publicly_accessible = False
        else:
            publicly_accessible = True

        self.vm_config = VMConfig(
            resource_id=self.resource_id,
            additional_outputs={"mysql_port": "3306", "password": self.password},
            docker_cfg=DockerConfig(
                image="mysql:latest",
                args=[],
                environment_variables={"MYSQL_ROOT_PASSWORD": self.password},
            ),
            instance_type=self.instance_type,
            disk_size_gb=self.disk_size_gb,
            firewall_cfg=FirewallConfig(expose_ports=[3306]),
            associate_public_ip_address=True,
            publicly_accessible=publicly_accessible,
        )
        return super().inputs(environment_state)

    def query(self, query: str):
        """Executes a SQL query on the MySQL instance running on the EC2 VM.

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
        """
        engine = self.sqlalchemy_engine()
        with engine.connect() as connection:
            result = connection.execute(text(query))
            connection.commit()
            if result.returns_rows:
                return result.fetchall()

    def django_settings(self):
        """Returns a Django settings dictionary for connecting to the MySQL instance running on EC2.

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
        """
        connection_info = self.outputs()
        return {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "mysql",
            "USER": "root",
            "PASSWORD": connection_info.additional_outputs.password,
            "HOST": self._get_host(connection_info),
            "PORT": connection_info.additional_outputs.mysql_port,
        }

    def sqlalchemy_engine_options(self):
        """Returns SQLAlchemy engine options for connecting to the MySQL instance running on EC2.

        **Returns:**
        - A dictionary of SQLAlchemy engine options.
        """
        if pymysql is None:
            raise ImportError(
                "pymysql is not installed. Please install it with `pip install pymysql`."
            )

        connection_info = self.outputs()
        host = self._get_host(connection_info)
        return {
            "url": f"mysql+pymysql://root:{connection_info.additional_outputs.password}@{host}:{connection_info.additional_outputs.mysql_port}/mysql",
        }

    async def sqlalchemy_async_engine_options(self):
        """Returns async SQLAlchemy engine options for connecting to the MySQL instance running on EC2.

        **Returns:**
        - A dictionary of async SQLAlchemy engine options.
        """
        if aiomysql is None:
            raise ImportError(
                "aiomysql is not installed. Please install it with `pip install aiomysql`."
            )

        connection_info = await self.outputs_async()
        host = self._get_host(connection_info)
        return {
            "url": f"mysql+aiomysql://root:{connection_info.additional_outputs.password}@{host}:{connection_info.additional_outputs.mysql_port}/mysql"
        }

    def sqlalchemy_engine(self, **engine_kwargs):
        """Returns a SQLAlchemy engine for connecting to a MySQL instance hosted on EC2.

        **Args:**
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - A SQLAlchemy engine.
        """
        if create_engine is None:
            raise ImportError(
                "SQLAlchemy is not installed. Please install it with "
                "`pip install sqlalchemy`."
            )

        engine_options = self.sqlalchemy_engine_options()
        engine_options.update(engine_kwargs)

        return create_engine(**engine_options)

    async def sqlalchemy_async_engine(self, **engine_kwargs):
        """Returns an async SQLAlchemy engine for connecting to a MySQL instance hosted on EC2.

        **Args:**
        - `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

        **Returns:**
        - An async SQLAlchemy engine.
        """
        if create_async_engine is None:
            raise ImportError(
                "SQLAlchemy asyncio extension is not installed. "
                "Please install it with `pip install sqlalchemy[asyncio]`."
            )

        engine_options = await self.sqlalchemy_async_engine_options()
        engine_options.update(engine_kwargs)

        return create_async_engine(**engine_options)
