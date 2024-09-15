import dataclasses
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Set

import yaml

import launchflow
from launchflow import exceptions
from launchflow.cache import cache
from launchflow.clients.file_client import read_file
from launchflow.config import config
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.models.enums import CloudProvider, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Inputs, Node, NodeType, T


@dataclasses.dataclass
class ResourceInputs(Inputs):
    resource_id: str


@dataclasses.dataclass
class _ResourceURI:
    project_name: str
    environment_name: str
    product: str
    resource_name: str
    cloud_provider: CloudProvider


def _to_output_type(outputs: Dict[str, Any], init_fn: Callable):
    fields = dataclasses.fields(init_fn)  # type: ignore
    # First filter so only the types matching the signature are passed
    filtered_outputs = {
        field.name: outputs[field.name] for field in fields if field.name in outputs
    }
    # gcp_id and aws_arn need to be handled separately so we remove from filtered_outputs
    gcp_id = filtered_outputs.pop("gcp_id", None)
    aws_arn = filtered_outputs.pop("aws_arn", None)
    # Next process any subdataclasses
    for field in fields:
        if dataclasses.is_dataclass(field.type):
            filtered_outputs[field.name] = _to_output_type(
                outputs[field.name], field.type
            )
    to_return = init_fn(**filtered_outputs)
    if gcp_id is not None or aws_arn is not None:
        to_return.gcp_id = gcp_id
        to_return.aws_arn = aws_arn
    return to_return


# Step 1: Check if the outputs should be fetched from a mounted volume
def _load_outputs_from_mounted_volume(resource_uri: _ResourceURI):
    if config.env.outputs_path is not None:
        local_resource_path = os.path.join(
            config.env.outputs_path, resource_uri.resource_name, "latest"
        )
        if not os.path.exists(local_resource_path):
            logging.warning(f"Outputs for resource '{resource_uri}' not found on disk.")
            return None
        else:
            with open(local_resource_path) as f:
                return yaml.safe_load(f)


# Step 2: Check the cache for outputs, otherwise fetch from remote
def _load_outputs_from_cache(resource_uri: _ResourceURI):
    resource_outputs = cache.get_resource_outputs(
        resource_uri.project_name,
        resource_uri.environment_name,
        resource_uri.product,
        resource_uri.resource_name,
    )
    if resource_outputs is not None:
        logging.debug(f"Using cached resource outputs for {resource_uri}")
        return resource_outputs


# Step 3a: Load artifact bucket from environment variable
def _get_artifact_bucket_path_from_local(resource_uri: _ResourceURI):
    if config.env.artifact_bucket is not None:
        # If the bucket env var is set, we use it to build the outputs path
        resource_outputs_bucket_path = (
            f"{config.env.artifact_bucket}/resources/{resource_uri.resource_name}.yaml"
        )
        logging.debug(
            f"Using Resource outputs bucket path built from environment variable for {resource_uri}"
        )
    else:
        # If the bucket env var is not set, we check the cache or fetch from remote
        resource_outputs_bucket_path = cache.get_resource_outputs_bucket_path(
            resource_uri.project_name,
            resource_uri.environment_name,
            resource_uri.product,
            resource_uri.resource_name,
        )
    return resource_outputs_bucket_path


def _resource_path_from_env(resource_uri: _ResourceURI, env: EnvironmentState) -> str:
    if resource_uri.cloud_provider == CloudProvider.GCP:
        if env.gcp_config is None:
            raise exceptions.GCPConfigNotFound(resource_uri.environment_name)
        bucket_url = f"gs://{env.gcp_config.artifact_bucket}"
    elif resource_uri.cloud_provider == CloudProvider.AWS:
        if env.aws_config is None:
            raise exceptions.AWSConfigNotFound(resource_uri.environment_name)
        bucket_url = f"s3://{env.aws_config.artifact_bucket}"

    return f"{bucket_url}/resources/{resource_uri.resource_name}.yaml"


async def _get_artifact_bucket_from_remote_async(resource_uri: _ResourceURI):
    em = EnvironmentManager(
        project_name=resource_uri.project_name,
        environment_name=resource_uri.environment_name,
        backend=config.launchflow_yaml.backend,
    )
    env = await em.load_environment()
    return _resource_path_from_env(resource_uri, env)


def _get_artifact_bucket_from_remote_sync(resource_uri: _ResourceURI):
    em = EnvironmentManager(
        project_name=resource_uri.project_name,
        environment_name=resource_uri.environment_name,
        backend=config.launchflow_yaml.backend,
    )
    env = em.load_environment_sync()
    return _resource_path_from_env(resource_uri, env)


def _load_outputs_from_remote_bucket(
    resource_outputs_bucket_path: str, resource_name: str
):
    try:
        resource_outputs = yaml.safe_load(read_file(resource_outputs_bucket_path))
    except Exception as e:
        raise exceptions.ResourceOutputsNotFound(resource_name) from e

    return resource_outputs


class Resource(Node[T]):
    product = ResourceProduct.UNKNOWN.value

    def __init__(
        self,
        name: str,
        replacement_arguments: Optional[Set[str]] = None,
        resource_id: Optional[str] = None,
        ignore_arguments: Optional[Set[str]] = None,
    ):
        super().__init__(name, NodeType.RESOURCE)
        self.name = name

        if replacement_arguments is None:
            replacement_arguments = set()
        self.replacement_arguments = replacement_arguments
        if ignore_arguments is None:
            ignore_arguments = set()
        self.ignore_arguments = ignore_arguments
        self.replacement_arguments.add("resource_id")
        if resource_id is None:
            self.resource_id = name
        else:
            self.resource_id = resource_id

    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __eq__(self, value) -> bool:
        return (
            isinstance(value, Resource)
            and value.name == self.name
            and value.product == self.product
            # TODO: Determine a better way to compare the inputs
            # Right now, we have to set the environment type to None which will
            # probably cause issues in the future
            # We should probably just have resource classes them selves define this
            and value.inputs(None) == self.inputs(None)  # type: ignore
            and value._outputs_type == self._outputs_type
        )

    def inputs(self, environment_state: EnvironmentState) -> ResourceInputs:
        raise NotImplementedError

    # TODO: Consider moving outputs logic to the base Node class. We should only do this
    # if we decide to start writing Service.outputs() to the bucket as well.
    def outputs(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> T:
        """
        Synchronously connect to the resource by fetching its outputs.
        """
        project_name = project or launchflow.project
        environment_name = environment or launchflow.environment
        if project_name is None or environment_name is None:
            raise exceptions.ProjectOrEnvironmentNotSet(project_name, environment_name)
        resource_uri = _ResourceURI(
            project_name,
            environment_name,
            self.product,
            self.name,
            self.cloud_provider(),
        )
        # Load outputs from mounted volume
        resource_outputs = _load_outputs_from_mounted_volume(resource_uri)
        if resource_outputs:
            return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore

        if use_cache:
            # Load outputs from cache
            resource_outputs = _load_outputs_from_cache(resource_uri)
            if resource_outputs:
                logging.debug(f"Loaded outputs from cache for {resource_uri}")
                return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore
            logging.debug(f"No outputs found in cache for {resource_uri}")

        # Load outputs from remote bucket
        artifact_bucket_path = _get_artifact_bucket_path_from_local(resource_uri)
        if artifact_bucket_path is None:
            artifact_bucket_path = _get_artifact_bucket_from_remote_sync(resource_uri)

        resource_outputs = _load_outputs_from_remote_bucket(
            artifact_bucket_path, resource_uri.resource_name
        )
        # NOTE: We still update the cache even if use_cache is False
        cache.set_resource_outputs(
            resource_uri.project_name,
            resource_uri.environment_name,
            resource_uri.product,
            resource_uri.resource_name,
            resource_outputs,
        )
        return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore

    async def outputs_async(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> T:
        """
        Asynchronously connect to the resource by fetching its outputs.
        """

        project_name = project or launchflow.project
        environment_name = environment or launchflow.environment
        resource_uri = _ResourceURI(
            project_name,
            environment_name,
            self.product,
            self.name,
            self.cloud_provider(),
        )
        # Load outputs from mounted volume
        resource_outputs = _load_outputs_from_mounted_volume(resource_uri)
        if resource_outputs:
            return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore

        if use_cache:
            # Load outputs from cache
            resource_outputs = _load_outputs_from_cache(resource_uri)
            if resource_outputs:
                logging.debug(f"Loaded outputs from cache for {resource_uri}")
                return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore
            logging.debug(f"No outputs found in cache for {resource_uri}")

        # Load outputs from remote bucket
        artifact_bucket_path = _get_artifact_bucket_path_from_local(resource_uri)
        if artifact_bucket_path is None:
            artifact_bucket_path = await _get_artifact_bucket_from_remote_async(
                resource_uri
            )

        resource_outputs = _load_outputs_from_remote_bucket(
            artifact_bucket_path, resource_uri.resource_name
        )
        # NOTE: We still update the cache even if use_cache is False
        cache.set_resource_outputs(
            resource_uri.project_name,
            resource_uri.environment_name,
            resource_uri.product,
            resource_uri.resource_name,
            resource_outputs,
        )
        return _to_output_type(resource_outputs, self._outputs_type)  # type: ignore

    # TODO: remove this method override once the Resources can depend on Services
    def inputs_depend_on(self, environment_state: EnvironmentState) -> List["Resource"]:  # type: ignore
        depends_on_nodes = super().inputs_depend_on(environment_state)
        for node in depends_on_nodes:
            if not node.is_resource():
                # TODO: remove the downstream assumpts that prevent Resources from depending on Services.
                # Most of the assumptions are in the planning / printing logic in create flow.
                raise ValueError(f"Resource {self.name} depends on non-resource {node}")
        return depends_on_nodes  # type: ignore
