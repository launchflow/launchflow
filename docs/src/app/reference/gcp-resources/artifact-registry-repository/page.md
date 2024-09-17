## ArtifactRegistryRepository

A resource for creating an artifact registry repository.
Can be used to store docker images, python packages, and more.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

### Example Usage

#### Create a docker repository
```python
import launchflow as lf

artifact_registry = lf.gcp.ArtifactRegistryRepository("my-artifact-registry", format="DOCKER")
```

#### Create a python repository
```python
import launchflow as lf

python_repository = lf.gcp.ArtifactRegistryRepository("my-python-repository", format="PYTHON")
```

#### Create a NPM repository
```python
import launchflow as lf

npm_repository = lf.gcp.ArtifactRegistryRepository("my-npm-repository", format="NPM")
```

### initialization

Create a new ArtifactRegistryRepository resource.

**Args:**
- `name (str)`: The name of the ArtifactRegistryRepository resource. This must be globally unique.
- `format (Union[str, RegistryFormat])`: The format of the ArtifactRegistryRepository.
- `location (Optional[str])`: The location of the ArtifactRegistryRepository. Defaults to the default region of the GCP project.
