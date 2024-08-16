# Handling imports and missing dependencies
try:
    import redis
except ImportError:
    redis = None  # type: ignore

from dataclasses import dataclass
from typing import Dict

from launchflow.docker.resource import DockerResource
from launchflow.node import Inputs, Outputs


def _check_redis_installs():
    if redis is None:
        raise ImportError(
            "redis library is not installed. Please install it with `pip install redis`."
        )


@dataclass
class DockerRedisOutputs(Outputs):
    container_id: str
    password: str
    ports: Dict[str, int]


@dataclass
class DockerRedisInputs(Inputs):
    password: str
    ports: Dict[str, int]


class DockerRedis(DockerResource[DockerRedisOutputs]):
    def __init__(self, name: str, *, password: str = "password") -> None:
        """A Redis resource running in a Docker container.

        **Args:**
        - `name` (str): The name of the Redis docker resource. This must be globally unique.
        - `password` (str): The password for the Redis DB. If not provided, a standard password will be used.

        **Example usage:**
        ```python
        import launchflow as lf

        redis = lf.DockerRedis("my-redis-instance")

        # Set a key-value pair
        client = redis.redis()
        client.set("my-key", "my-value")

        # Async compatible
        async_client = await redis.redis_async()
        await async_client.set("my-key", "my-value")
        ```
        """
        self.password = password

        super().__init__(
            name=name,
            env_vars={},
            command=f"redis-server --appendonly yes --requirepass {password}",
            ports={"6379/tcp": None},  # type: ignore
            docker_image="redis",
            running_container_id=None,  # Lazy-loaded
        )

        self._sync_client = None
        self._async_pool = None

    def inputs(self, *args, **kwargs) -> DockerRedisInputs:  # type: ignore
        self._lazy_load_container_info()
        return DockerRedisInputs(ports=self.ports, password=self.password)

    def django_settings(self):
        connection_info = self.outputs()
        return {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://default:{connection_info.password}@localhost:{connection_info.ports['6379/tcp']}",
        }

    def redis(self, **client_kwargs):
        """Get a Generic Redis Client object from the redis-py library.

        **Returns:**
        - The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.
        """
        _check_redis_installs()
        connection_info = self.outputs()
        if self._sync_client is None:
            self._sync_client = redis.Redis(
                host="localhost",
                port=int(connection_info.ports["6379/tcp"]),
                password=connection_info.password,
                **client_kwargs,
            )
        return self._sync_client

    async def redis_async(self, *, decode_responses: bool = True):
        """Get an Async Redis Client object from the redis-py library.

        **Returns:**
        - The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.
        """
        _check_redis_installs()
        connection_info = await self.outputs_async()
        if self._async_pool is None:
            self._async_pool = await redis.asyncio.from_url(  # type: ignore
                f"redis://localhost:{connection_info.ports['6379/tcp']}",
                password=connection_info.password,
                decode_responses=decode_responses,
            )
        return self._async_pool
