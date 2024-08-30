## GlobalIPAddress

A global ip address resource.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/compute/docs/ip-addresses).

### Example Usage
```python
import launchflow as lf

ip = lf.gcp.GlobalIPAddress("ip-addres")
```

### initialization

Create a new Global IP Address resource.

**Args:**
- `name (str)`: The name of the ip address.
