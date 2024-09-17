# Handling imports and missing dependencies
try:
    import redis
except ImportError:
    redis = None  # type: ignore

# Importing the required modules

import dataclasses
from typing import Optional

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.generic_clients import RedisClient
from launchflow.models.enums import EnvironmentType, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


def _check_installs():
    if redis is None:
        raise ImportError(
            "redis library is not installed. Please install it with `pip install redis`."
        )


@dataclasses.dataclass
class ElasticacheRedisOutputs(Outputs):
    host: str
    port: int
    password: str


@dataclasses.dataclass
class ElasticacheRedisInputs(ResourceInputs):
    node_type: str
    parameter_group_name: str
    engine_version: str


class ElasticacheRedis(AWSResource[ElasticacheRedisOutputs], RedisClient):
    """A Redis cluster running on AWS's Elasticache service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/elasticache/).

    **NOTE**: This resource can only be accessed from within the same VPC it is created in.
    Use [EC2Redis](/reference/aws-resources/ec2#ec-2-redis) to create a Redis instance that can be accessed from outside the VPC.

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to an Elasticache Redis cluster in your AWS account
    elasticache = lf.aws.ElasticacheRedis("my-redis-cluster")

    # Set a key-value pair
    client = elasticache.redis()
    client.set("my-key", "my-value")

    # Async compatible
    async_client = await elasticache.redis_async()
    await async_client.set("my-key", "my-value")
    ```
    """

    product = ResourceProduct.AWS_ELASTICACHE_REDIS.value

    def __init__(
        self,
        name: str,
        node_type: Optional[str] = None,
        parameter_group_name: str = "default.redis7",
        engine_version: str = "7.0",
    ) -> None:
        """Create a new Elasticache Redis resource.

        **Args:**
        - `name (str)`: The name of the Elasticache Redis cluster.
        - `node_type (Optional[str])`: The instance class of the Elasticache Redis cluster. Defaults to `cache.t4g.micro` for development environments and `cache.r7g.large` for production environments.
        - `parameter_group_name (str)`: The name of the parameter group to associate with the Elasticache Redis cluster. Defaults to `default.redis7`.
        - `engine_version (str)`: Version number of the cache engine to use. Defaults to `7.0`.
        """
        super().__init__(name=name, resource_id=f"{name}-{lf.project}-{lf.environment}")
        self.parameter_group_name = parameter_group_name
        self.node_type = node_type
        self.engine_version = engine_version

    def inputs(self, environment_state: EnvironmentState) -> ElasticacheRedisInputs:
        node_type = self.node_type
        if node_type is None:
            if environment_state.environment_type == EnvironmentType.DEVELOPMENT:
                node_type = "cache.t4g.micro"
            else:
                node_type = "cache.r7g.large"
        return ElasticacheRedisInputs(
            resource_id=self.resource_id,
            node_type=node_type,
            parameter_group_name=self.parameter_group_name,
            engine_version=self.engine_version,
        )

    def django_settings(self):
        """Returns a Django settings dictionary for connecting to the Elasticache Redis cluster.

        **Returns:**
        - A dictionary of Django settings for connecting to the Elasticache Redis cluster.

        **Example usage:**
        ```python
        import launchflow as lf

        elasticache = lf.aws.ElasticacheRedis("my-redis-cluster")

        # settings.py
        CACHES = {
            # Connect Django's cache backend to the Elasticache Redis cluster
            "default": elasticache.django_settings(),
        }
        ```
        """
        connection_info = self.outputs()
        return {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            # NOTE: We use rediss:// to connect to a Redis cluster with TLS enabled.
            "LOCATION": f"rediss://default:{connection_info.password}@{connection_info.host}:{connection_info.port}",
        }

    def redis(self):
        """Get a Generic Redis Client object from the redis-py library.

        **Returns:**
        - The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.
        """
        _check_installs()
        connection_info = self.outputs()
        return redis.Redis(
            host=connection_info.host,
            port=connection_info.port,
            password=connection_info.password,
            decode_responses=True,
            # NOTE: We use ssl=True to connect to a Redis cluster with TLS enabled.
            ssl=True,
        )

    async def redis_async(self):
        """Get an Async Redis Client object from the redis-py library.

        **Returns:**
        - The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.
        """
        _check_installs()
        connection_info = await self.outputs_async()
        return await redis.asyncio.from_url(
            # NOTE: We use rediss:// to connect to a Redis cluster with TLS enabled.
            f"rediss://{connection_info.host}:{connection_info.port}",
            password=connection_info.password,
            decode_responses=True,
        )
