## MemorystoreRedis

A Redis cluster running on Google Cloud's Memorystore service.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/memorystore/docs/redis).

**NOTE**: This resource can only be accessed from within the same VPC it is created in.
Use [ComputeEngineRedis](/reference/gcp-resources/compute-engine#compute-engine-redis) to create a Redis instance that can be accessed from outside the VPC.

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to a Memorystore Redis cluster in your GCP project
memorystore = lf.gcp.MemorystoreRedis("my-redis-cluster")

# Set a key-value pair
client = memorystore.redis()
client.set("my-key", "my-value")

# Async compatible
async_client = await memorystore.redis_async()
await async_client.set("my-key", "my-value")
```

### initialization

Create a new Memorystore Redis resource.

**Args:**
- `name (str)`: The name of the Redis VM resource. This must be globally unique.
- `memory_size_gb (int)`: The memory size of the Redis instance in GB. Defaults to 1.

### django\_settings

```python
MemorystoreRedis.django_settings()
```

Returns a Django settings dictionary for connecting to the Memorystore Redis cluster.

**Example usage:**
```python
import launchflow as lf

memorystore = lf.gcp.MemorystoreRedis("my-redis-cluster")

# settings.py
CACHES = {
    # Connect Django's cache backend to the Memorystore Redis cluster
    "default": memorystore.django_settings(),
}
```

### redis

```python
MemorystoreRedis.redis()
```

Get a Generic Redis Client object from the redis-py library.

**Returns:**
- The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.

### redis\_async

```python
async MemorystoreRedis.redis_async()
```

Get an Async Redis Client object from the redis-py library.

**Returns:**
- The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.
