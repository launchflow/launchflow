## ElasticacheRedis

A Redis cluster running on AWS's Elasticache service.

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

### initialization

Create a new Elasticache Redis resource.

**Args:**
- `name (str)`: The name of the Elasticache Redis cluster.
- `node_type (Optional[str])`: The instance class of the Elasticache Redis cluster. Defaults to `cache.t4g.micro` for development environments and `cache.r7g.large` for production environments.
- `parameter_group_name (str)`: The name of the parameter group to associate with the Elasticache Redis cluster. Defaults to `default.redis7`.
- `engine_version (str)`: Version number of the cache engine to use. Defaults to `7.0`.

### inputs

```python
ElasticacheRedis.inputs(environment_state: EnvironmentState) -> ElasticacheRedisInputs
```

Get the inputs for the Elasticache Redis resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for.

**Returns:**
- `ElasticacheRedisInputs`: The inputs for the Elasticache Redis resource.

### django\_settings

```python
ElasticacheRedis.django_settings()
```

Returns a Django settings dictionary for connecting to the Elasticache Redis cluster.

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

### redis

```python
ElasticacheRedis.redis()
```

Get a Generic Redis Client object from the redis-py library.

**Returns:**
- The [Generic Redis Client](https://redis-py.readthedocs.io/en/stable/connections.html#generic-client) from the redis-py library.

### redis\_async

```python
async ElasticacheRedis.redis_async()
```

Get an Async Redis Client object from the redis-py library.

**Returns:**
- The [Async Redis Client object](https://redis-py.readthedocs.io/en/stable/connections.html#async-client) from the redis-py library.
