## GKECustomDomainMapping

A resource for mapping a custom domain to a service hosted on GKE.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

### Example Usage
```python

import launchflow as lf

ip_address = lf.gcp.GlobalIPAddress("my-global-ip-address")
ssl_certificate = lf.gcp.ManagedSSLCertificate("my-ssl-certificate", domains=["example.com"])
cluster = lf.gcp.GKECluster("my-gke-cluster")
service = lf.gcp.GKECloudRunService("my-gke-cloud-run-service", cluster=cluster)
custom_domain_mapping = lf.gcp.GKECustomDomainMapping(
    "my-custom-domain-mapping",
    ip_address=ip_address,
    ssl_certificate=ssl_certificate,
    service_container=service.container,
)
```

### initialization

Create a new CustomDomainMapping resource.

**Args:**
- `name` (str): The name of the CustomDomainMapping resource. This must be globally unique.
- `ssl_certificate (ManagedSSLCertificate):` The [SSL certificate](/reference/gcp-resources/ssl) to use for the domain.
- `ip_address (GlobalIPAddress)`: The [IP address](/reference/gcp-resources/global-ip-address) to map the domain to.
- `service_container (ServiceContainer)`: The [ServiceContainer](/reference/kubernetes-resources/service) to map the domain to.
