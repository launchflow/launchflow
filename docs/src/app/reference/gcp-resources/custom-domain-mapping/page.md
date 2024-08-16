## CustomDomainMapping

A resource for mapping a custom domain to a Cloud Run service.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

### Example Usage
```python
import launchflow as lf

custom_domain_mapping = lf.gcp.CustomDomainMapping("my-custom-domain-mapping", domain="my-domain.com", cloud_run=lf.gcp.CloudRunServiceContainer("my-cloud-run-service"))
```

### initialization

Create a new CustomDomainMapping resource.

**Args:**
- `name` (str): The name of the CustomDomainMapping resource. This must be globally unique.
- `domain` (str): The domain to map to the Cloud Run service.
- `cloud_run` (CloudRunServiceContainer): The Cloud Run service to map the domain to. One and only one of cloud_run and gce_service must be provided.
- `regional_managed_instance_group` (RegionalManagedInstanceGroup): The Compute Engine service to map the domain to. One and only one of cloud_run and gce_service must be provided.

### inputs

```python
CustomDomainMapping.inputs(environment_state: EnvironmentState) -> CustomDomainMappingInputs
```

Get the inputs for the Custom Domain Mapping resource.

**Args:**
- `environment_type` (EnvironmentType): The type of environment.

**Returns:**
- CustomDomainMappingInputs: The inputs for the Custom Domain Mapping resource.
