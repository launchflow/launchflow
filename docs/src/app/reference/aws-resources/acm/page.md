## ACMCertificate

An ACM Certificate resource.

**Note:** This Resource is in beta and is likely to change in the future.

For more information see [the official documentation](https://docs.aws.amazon.com/acm/).

### Example Usage
```python
import launchflow as lf

certificate = lf.aws.ACMCertificate("my-certificate")
```

### initialization

Creates a new ACM Certificate resource.

**Args:**
- `name (str)`: The name of the resource.
- `domain_name (str)`: The domain name to use for the certificate.

### inputs

```python
ACMCertificate.inputs(environment_state: EnvironmentState) -> ACMCertificateInputs
```

Get the inputs for the ACM Certificate.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for.

**Returns:**
- An `ACMCertificateInputs` object containing the inputs for the ACM Certificate.
