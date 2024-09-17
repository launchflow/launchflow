## SecretsManagerSecret

A Secrets Manager Secret resource.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://docs.aws.amazon.com/secretsmanager/).


### Example Usage
```python
import launchflow as lf

# Automatically configures a SecretsManager Secret in your AWS account
secret = lf.aws.SecretsManagerSecret("my-secret")
# Get the latest version of the secret
value = secret.version()
```

### initialization

Create a new Secrets Manager Secret resource.

**Args:**
- `name (str)`: The name of the secret.
- `recovery_window_in_days (int)`: The number of days that AWS Secrets Manager waits before it can delete the secret. Defaults to 30 days. If 0 is provided, the secret can be deleted immediately.

### version

```python
SecretsManagerSecret.version(version_id: Optional[str] = None, use_cache: bool = False) -> str
```

Get the secret version from the Secrets Manager.

**Args:**
- `version_id (Optional[str])`: The version of the secret to get. If not provided, the latest version is returned.
- `use_cache (bool)`: Whether to cache the value of the secret in memory. Defaults to False.

**Returns:**
- The value associated with the secret version.

**Example usage:**

```python
import launchflow as lf

secret = lf.aws.SecretsManagerSecret("my-secret")
value = secret.version()
```

### add\_version

```python
SecretsManagerSecret.add_version(payload: str)
```

Adds a new version of the secret to the Secrets Manager.

**Args:**
- `payload (str)`: The value to add to the secret.

**Example usage:**

```python
import launchflow as lf

secret = lf.aws.SecretsManagerSecret("my-secret")
secret.add_version("my-new-value")
```
