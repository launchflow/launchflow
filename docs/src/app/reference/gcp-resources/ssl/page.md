## ManagedSSLCertificate

A manage ssl certificate resource.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs).

### Example Usage
```python
import launchflow as lf

ip = lf.gcp.GlobalIPAddress("ip-addres")
```

### initialization

Create a new managed ssl certificate resource.

**Args:**
- `name (str)`: The name of the ip address.
- `domain (str)`: The domain of the ssl certificate.
