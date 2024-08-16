## ECRRepository

A resource for creating an ECR repository.
Can be used to store container images.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

### Example Usage
```python
import launchflow as lf

ecr_repository = lf.aws.ECRRepository("my-ecr-repository")
```

### initialization

Create a new ECRRepository resource.

**Args:**
- `name (str)`: The name of the ECRRepository resource. This must be globally unique.
- `force_delete (bool)`: Whether to force delete the repository when the environment is deleted. Defaults to True.
- `image_tag_mutability (Literal["MUTABLE", "IMMUTABLE"])`: The image tag mutability for the repository. Defaults to "MUTABLE"

### inputs

```python
ECRRepository.inputs(environment_state: EnvironmentState) -> ECRRepositoryInputs
```

Get the inputs required for the ECR repository.

**Args:**
- `environment_state` (EnvironmentState): The environment to get the inputs for.

**Returns:**
- An `ECRRepositoryInputs` object containing the inputs for the ECR repository.
