## CustomDomainMapping

A resource for mapping a custom domain to a Cloud Run service or a compute engine service.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

### Example Usage
```python
import launchflow as lf

ip_address = lf.gcp.GlobalIPAddress("my-global-ip-address")
ssl_certificate = lf.gcp.ManagedSSLCertificate("my-ssl-certificate", domains=["example.com"])
custom_domain_mapping = lf.gcp.CustomDomainMapping(
    "my-custom-domain-mapping",
    ip_address=ip_address,
    ssl_certificate=ssl_certificate,
    cloud_run=lf.gcp.CloudRunServiceContainer("my-cloud-run-service"
)
```

### initialization

Create a new CustomDomainMapping resource.

**Args:**
- `name (str)`: The name of the CustomDomainMapping resource. This must be globally unique.
- `ssl_certificate (ManagedSSLCertificate):` The [SSL certificate](/reference/gcp-resources/ssl) to use for the domain.
- `ip_address (GlobalIPAddress)`: The [IP address](/reference/gcp-resources/global-ip-address) to map the domain to.
- `cloud_run (CloudRunServiceContainer)`: The Cloud Run service to map the domain to. One and only one of cloud_run and gce_service must be provided.
- `regional_managed_instance_group (RegionalManagedInstanceGroup)`: The Compute Engine service to map the domain to. One and only one of cloud_run and gce_service must be provided.
- `include_http_redirect (bool)`: Whether to include an HTTP redirect to the HTTPS URL. Defaults to True.
