## SecretManagerSecret

A Secret Manager secret resource.

This creates the container for the secret and allows you to access the secret's value. You will need to manually add a value to the secret.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/secret-manager/docs/overview).

### Example Usage
```python
import launchflow as lf

# Automatically configures a SecretManager Secret in your GCP project
api_key = lf.gcp.SecretManagerSecret("api-key")
# Get the latest version of the secret
value = secret.version()
```

### initialization

Create a new Secret Manager secret resource.

**Args:**
- `name (str)`: The name of the secret.

### version

```python
SecretManagerSecret.version(version: str = "latest", use_cache: bool = False) -> bytes
```

Access a version of the secret.

**Args:**
- `version (str)`: The version of the secret to access. Defaults to "latest".
- `use_cache (bool)`: Whether to cache the value of the secret in memory. Defaults to False.

**Returns:**
- The value of the secret as bytes.

**Example usage:**

```python
import launchflow as lf

api_key = lf.gcp.SecretManagerSecret("api-key")
secret = api_key.version()
```

### add\_version

```python
SecretManagerSecret.add_version(payload: bytes)
```

Add a version of the secret.

**Args:**
- `payload (bytes)`: The payload to add to the secret.

**Example usage:**

```python
import launchflow as lf

api_key = lf.gcp.SecretManagerSecret("api-key")
api_key.add_version(open("api-key.txt", "rb").read())
```
