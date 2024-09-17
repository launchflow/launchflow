import asyncio
import dataclasses
import datetime
import io
import logging
import os
import time
from typing import Any, List, Literal, Optional, Tuple, Union

import rich
from rich.console import Console
from rich.live import Live
from rich.padding import Padding
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.table import Table
from rich.tree import Tree

import launchflow
from launchflow import exceptions
from launchflow.aws.service import AWSService
from launchflow.cli.resource_utils import is_secret_resource
from launchflow.clients.docker_client import docker_service_available
from launchflow.config import config
from launchflow.flows.create_flows import (
    CreateResourcePlan,
    CreateResourceResult,
    CreateServicePlan,
    CreateServiceResult,
    plan_create,
    plan_create_service,
)
from launchflow.flows.flow_utils import (
    OP_COLOR,
    EnvironmentRef,
    ResourceRef,
    ServiceRef,
    format_configuration_dict,
)
from launchflow.flows.generate_dockerfile import generate_dockerfile
from launchflow.flows.plan import (
    FailedToPlan,
    FlowResult,
    Plan,
    Result,
    ServicePlan,
    execute_plans,
)
from launchflow.flows.plan_utils import lock_plans, print_plans, select_plans
from launchflow.gcp.cloud_run import CloudRunService
from launchflow.gcp.compute_engine_service import ComputeEngineService
from launchflow.gcp.firebase_site import FirebaseStaticSite
from launchflow.gcp.gke_service import GKEService
from launchflow.gcp.service import GCPDockerService, GCPService
from launchflow.gcp.static_site import GCSWebsite
from launchflow.locks import Lock, LockOperation, OperationType, ReleaseReason
from launchflow.managers.environment_manager import EnvironmentManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.enums import CloudProvider, EnvironmentStatus, ServiceStatus
from launchflow.models.flow_state import (
    AWSEnvironmentConfig,
    EnvironmentState,
    GCPEnvironmentConfig,
    ServiceState,
)
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Node
from launchflow.resource import Resource
from launchflow.service import DockerService, Service
from launchflow.utils import dump_exception_with_stacktrace, generate_deployment_id
from launchflow.validation import validate_service_name
from launchflow.workflows.deploy_gcp_service import (
    build_and_push_gcp_service,
    deploy_local_files_to_firebase_static_site,
    promote_gcp_service_image,
    release_docker_image_to_cloud_run,
    release_docker_image_to_compute_engine,
    release_docker_image_to_gke,
    upload_local_files_to_static_site,
)


@dataclasses.dataclass
class BuildServiceResult(Result["BuildServicePlan"]):
    docker_image: Optional[str] = None
    logs_file_or_link: Optional[str] = None
    build_outputs: Optional[Any] = None


@dataclasses.dataclass
class BuildServicePlan(ServicePlan):
    service_manager: ServiceManager
    environment_state: EnvironmentState
    deployment_id: str
    build_local: bool = False

    def __post_init__(self):
        if (
            isinstance(self.service, GCPService)
            and self.environment_state.gcp_config is None
        ):
            raise ValueError(
                "GCP environment config must set on the EnvironmentState to build a GCP service."
            )
        if (
            isinstance(self.service, AWSService)
            and self.environment_state.aws_config is None
        ):
            raise ValueError(
                "AWS environment config must set on the EnvironmentState to build an AWS service."
            )

    @property
    def operation_type(self) -> Literal["build"]:
        return "build"

    async def abandon_plan(self, reason: str):
        result = BuildServiceResult(plan=self, success=False)
        result.error_message = f"Build abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> BuildServiceResult:
        try:
            logs_file_or_link = None
            if isinstance(self.service, GCPDockerService):
                docker_image, logs_file_or_link = await build_and_push_gcp_service(
                    self.service,
                    self.service_manager,
                    self.environment_state.gcp_config,  # type: ignore
                    self.deployment_id,
                    self.build_local,
                )
                return BuildServiceResult(self, True, docker_image, logs_file_or_link)

            # TODO: Remove the isintance checks once GCP services are refactored to implement the build method
            elif isinstance(self.service, AWSService):
                # TODO: Move this to the top of the flow once GCP services are refactored to implement the build method
                base_logging_dir = "/tmp/launchflow"
                os.makedirs(base_logging_dir, exist_ok=True)
                build_logs_file = (
                    f"{base_logging_dir}/{self.service.name}-{int(time.time())}.log"
                )
                with open(build_logs_file, "w") as build_log_file:
                    try:
                        build_outputs = await self.service.build(
                            environment_state=self.environment_state,
                            launchflow_uri=LaunchFlowURI(
                                project_name=self.service_manager.project_name,
                                environment_name=self.service_manager.environment_name,
                                service_name=self.service_manager.service_name,
                            ),
                            deployment_id=self.deployment_id,
                            build_log_file=build_log_file,
                            build_local=self.build_local,
                        )
                    except Exception as e:
                        dump_exception_with_stacktrace(e, build_log_file)
                        # TODO: Move the try catch up to the top of the flow once the GCPServices are refactored to implement the build method
                        raise exceptions.ServiceBuildFailed(
                            error_message=str(e),
                            build_logs_or_link=build_logs_file,
                        ) from e
                return BuildServiceResult(self, True, build_outputs=build_outputs)
            elif isinstance(self.service, GCPService):
                # TODO: Add a hook to allow for custom build steps for static sites
                return BuildServiceResult(self, True)
            else:
                result = BuildServiceResult(self, False)
                result.error_message = f"Unsupported service type: {self.service}"
                return result
        except exceptions.ServiceBuildFailed as e:
            # TODO: Use dump_exception_with_stacktrace to dump the stack trace to the log file
            result = BuildServiceResult(
                self, False, logs_file_or_link=e.build_logs_or_link
            )
            result.error_message = str(e)
            return result
        except Exception as e:
            # TODO: Improve this error handling
            logging.error("Exception occurred: %s", e, exc_info=True)
            result = BuildServiceResult(self, False)
            result.error_message = str(e)
            return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        left_padding_str = " " * left_padding

        build_inputs_dict = {
            "build_directory": self.service.build_directory,
            "build_ignore": self.service.build_ignore,
            "build_local": self.build_local,
        }
        # This is what allows child classes to add additional build args to the plan
        build_inputs_dict.update(self.service.build_diff_args)

        build_inputs_str = format_configuration_dict(build_inputs_dict)
        console.print()
        console.print(
            f"{left_padding_str}1. {ServiceRef(self.service)} will be [{OP_COLOR}]built[/{OP_COLOR}] with the following configuration:"
        )
        console.print(
            left_padding_str
            + "    "
            + f"\n{left_padding_str}    ".join(build_inputs_str.split("\n"))
        )

    async def lock_plan(self) -> None:
        return None

    def pending_message(self):
        return f"Build {ServiceRef(self.service)} waiting for create step to finish..."

    def task_description(self):
        return f"Building {ServiceRef(self.service)}..."

    def success_message(self):
        return f"Successfully built {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to build {ServiceRef(self.service)}"


@dataclasses.dataclass
class ReleaseServiceResult(Result["ReleaseServicePlan"]):
    service_url: Optional[str] = None


@dataclasses.dataclass
class ReleaseServicePlan(ServicePlan):
    environment_ref: EnvironmentRef
    service_manager: ServiceManager
    environment_state: EnvironmentState
    deployment_id: str
    build_step_type: Optional[Literal["build", "promote"]]

    def __post_init__(self):
        if (
            isinstance(self.service, GCPService)
            and self.environment_state.gcp_config is None
        ):
            raise ValueError(
                "GCP environment config must be set on the EnvironmentState to release a GCP service."
            )
        if (
            isinstance(self.service, AWSService)
            and self.environment_state.aws_config is None
        ):
            raise ValueError(
                "AWS environment config must be set on the EnvironmentState to release an AWS service."
            )

    @property
    def operation_type(self) -> Literal["release"]:
        return "release"

    async def abandon_plan(self, reason: str):
        result = ReleaseServiceResult(plan=self, success=False)
        result.error_message = f"Release abandoned: {reason}"
        return result

    def _get_docker_image_from_dependency(
        self, dependency_results: List[Result]
    ) -> Union[ReleaseServiceResult, str]:
        # TODO: if docker step is None then get the docker image from the service
        if self.build_step_type == "build":
            docker_result_type = BuildServiceResult
        else:
            docker_result_type = PromoteDockerImageResult  # type: ignore
        docker_image_result = next(
            (
                result
                for result in dependency_results
                if isinstance(result, docker_result_type)
            ),
            None,
        )
        if docker_image_result is None:
            result = ReleaseServiceResult(self, False)
            result.error_message = "Could not find a docker image result to release"
            return result
        if docker_image_result.docker_image is None:
            result = ReleaseServiceResult(self, False)
            result.error_message = "Docker image step did not produce a docker image"
            return result
        return docker_image_result.docker_image

    def _get_build_outputs_from_dependency(
        self, dependency_results: List[Result]
    ) -> Union[ReleaseServiceResult, Any]:
        if self.build_step_type == "build":
            build_result_type = BuildServiceResult
        else:
            raise ValueError("Cannot get build outputs from a promote step")
        build_outputs_result = next(
            (
                result
                for result in dependency_results
                if isinstance(result, build_result_type)
            ),
            None,
        )
        if build_outputs_result is None:
            result = ReleaseServiceResult(self, False)
            result.error_message = "Could not find a build outputs result to release"
            return result
        if build_outputs_result.build_outputs is None:
            result = ReleaseServiceResult(self, False)
            result.error_message = "Build step did not produce build outputs"
            return result
        return build_outputs_result.build_outputs

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> ReleaseServiceResult:
        try:
            # TODO: Consider refactoring this to separate static & docker release steps
            if isinstance(self.service, GCSWebsite):
                service_url = await upload_local_files_to_static_site(
                    gcp_environment_config=self.environment_state.gcp_config,  # type: ignore
                    static_site=self.service,
                )
                return ReleaseServiceResult(self, True, service_url)

            if isinstance(self.service, FirebaseStaticSite):
                service_url = await deploy_local_files_to_firebase_static_site(
                    gcp_environment_config=self.environment_state.gcp_config,  # type: ignore
                    firebase_static_site=self.service,
                )
                return ReleaseServiceResult(self, True, service_url)

            # TODO: Remove the isintance checks once GCP services are refactored to implement the release method
            if isinstance(self.service, AWSService):
                # TODO: Remove this hacky check once we remove DockerService and can just pass the Any through to release()
                build_outputs = self._get_build_outputs_from_dependency(
                    dependency_results
                )
                if isinstance(build_outputs, ReleaseServiceResult):
                    result = ReleaseServiceResult(self, False)
                    result.error_message = (
                        f"Failed to find build outputs for {self.service}"
                    )
                    return result

                # TODO: Move this to the top of the flow once GCP services are refactored to implement the release method
                base_logging_dir = "/tmp/launchflow"
                os.makedirs(base_logging_dir, exist_ok=True)
                release_logs_file = (
                    f"{base_logging_dir}/{self.service.name}-{int(time.time())}.log"
                )
                with open(release_logs_file, "w") as release_log_file:
                    try:
                        await self.service.release(
                            release_inputs=build_outputs,
                            environment_state=self.environment_state,
                            launchflow_uri=LaunchFlowURI(
                                project_name=self.service_manager.project_name,
                                environment_name=self.service_manager.environment_name,
                                service_name=self.service_manager.service_name,
                            ),
                            deployment_id=self.deployment_id,
                            release_log_file=release_log_file,
                        )
                    except Exception as e:
                        dump_exception_with_stacktrace(e, release_log_file)
                        # TODO: Move the try catch up to the top of the flow once the GCPServices are refactored to implement the release method
                        raise exceptions.ServiceReleaseFailed(
                            error_message=f"Failed to release {self.service}",
                            release_logs_or_link=release_logs_file,
                        ) from e

                return ReleaseServiceResult(
                    self, True, self.service.outputs().service_url
                )

            if self.build_step_type is not None:
                maybe_docker_image = self._get_docker_image_from_dependency(
                    dependency_results
                )
                if isinstance(maybe_docker_image, ReleaseServiceResult):
                    return maybe_docker_image
                docker_image = maybe_docker_image
            else:
                service_state = await self.service_manager.load_service()
                docker_image = service_state.docker_image  # type: ignore
                if docker_image is None:
                    result = ReleaseServiceResult(self, False)
                    result.error_message = "Service does not yet have a docker image. Ensure you have run `lf deploy` first."
                    return result
            # TODO: refactor this so that the service "owns" the release step so its not hardcoded to individual service types
            if isinstance(self.service, CloudRunService):
                service_url = await release_docker_image_to_cloud_run(
                    docker_image=docker_image,
                    service_manager=self.service_manager,
                    gcp_environment_config=self.environment_state.gcp_config,  # type: ignore
                    cloud_run_service=self.service,
                    deployment_id=self.deployment_id,
                )
            elif isinstance(self.service, ComputeEngineService):
                service_url = await release_docker_image_to_compute_engine(
                    docker_image=docker_image,
                    service_manager=self.service_manager,
                    gcp_environment_config=self.environment_state.gcp_config,  # type: ignore
                    compute_engine_service=self.service,
                    deployment_id=self.deployment_id,
                )
            elif isinstance(self.service, GKEService):
                service_url = await release_docker_image_to_gke(
                    docker_image=docker_image,
                    service_manager=self.service_manager,
                    gcp_environment_config=self.environment_state.gcp_config,  # type: ignore
                    gke_service=self.service,
                    deployment_id=self.deployment_id,
                )
            else:
                result = ReleaseServiceResult(self, False)
                result.error_message = f"Unsupported service type: {self.service}"
                return result
            return ReleaseServiceResult(self, True, service_url)
        except exceptions.ServiceReleaseFailed as e:
            result = ReleaseServiceResult(self, False)
            result.error_message = str(e)
            return result
        except Exception as e:
            # TODO: Improve this error handling
            logging.error("Exception occurred: %s", e, exc_info=True)
            result = ReleaseServiceResult(self, False)
            result.error_message = str(e)
            return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
        step_number: int = 2,
    ):
        service_inputs = self.service.inputs().to_dict()
        left_padding_str = " " * left_padding

        base_msg = f"{left_padding_str}{step_number}. {ServiceRef(self.service)} will be [{OP_COLOR}]released[/{OP_COLOR}] to {self.environment_ref}."
        if service_inputs:
            pretty_inputs = format_configuration_dict(service_inputs)
            pretty_inputs = f"\n{left_padding_str}    ".join(pretty_inputs.split("\n"))
            base_msg += f" With the following configuration:\n{left_padding_str}    {pretty_inputs}"

        console.print(base_msg)
        console.print()

    async def lock_plan(self) -> None:
        return None

    def pending_message(self):
        return f"Release {ServiceRef(self.service)} waiting for build step to finish..."

    def task_description(self):
        return f"Releasing {ServiceRef(self.service)}..."

    def success_message(self):
        return f"Successfully released {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to release {ServiceRef(self.service)}"


@dataclasses.dataclass
class DeployServiceResult(Result["DeployServicePlan"]):
    service_state: Optional[ServiceState]
    build_result: Optional[BuildServiceResult]
    release_result: ReleaseServiceResult


@dataclasses.dataclass
class DeployServicePlan(ServicePlan):
    service_manager: ServiceManager
    existing_service_state: Optional[ServiceState]
    build_service_plan: Optional[BuildServicePlan]
    release_service_plan: ReleaseServicePlan
    _lock: Optional[Lock] = None

    def child_plans(self) -> List[Plan]:
        child_plans: List[Plan] = []
        if self.build_service_plan is not None:
            child_plans.append(self.build_service_plan)
        child_plans.append(self.release_service_plan)
        return child_plans

    @property
    def operation_type(self) -> Literal["deploy"]:
        return "deploy"

    async def abandon_plan(self, reason: str):
        if self._lock is not None:
            await self._lock.release(ReleaseReason.ABANDONED)

        abandon_tasks = []
        if self.build_service_plan is not None:
            abandon_tasks.append(self.build_service_plan.abandon_plan(reason))
        abandon_tasks.append(self.release_service_plan.abandon_plan(reason))
        build_service_result, release_service_result = await asyncio.gather(
            *abandon_tasks
        )

        result = DeployServiceResult(
            self,
            False,
            None,
            build_service_result,
            release_service_result,
        )
        result.error_message = f"Deploy abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> DeployServiceResult:
        if self._lock is None:
            return await self.abandon_plan("Plan was not locked before execution.")
        try:
            self.service.outputs()
        except exceptions.ServiceOutputsNotFound:
            return await self.abandon_plan(
                "Service outputs not found. This usually means the service was not created successfully."
            )

        async with self._lock as lock_info:
            updated_time = datetime.datetime.now(datetime.timezone.utc)
            if self.existing_service_state:
                created_time = self.existing_service_state.created_at
                inputs = self.existing_service_state.inputs
                gcp_id = self.existing_service_state.gcp_id
                aws_arn = self.existing_service_state.aws_arn
                service_url = self.existing_service_state.service_url
                docker_image = self.existing_service_state.docker_image
            else:
                created_time = updated_time
                # NOTE: We dont save the inputs until the deploy is successful
                inputs = None
                gcp_id = None
                aws_arn = None
                service_url = None
                docker_image = None

            new_service_state = ServiceState(
                name=self.service.name,
                product=self.service.product,
                cloud_provider=self.service.cloud_provider(),
                created_at=created_time,
                updated_at=updated_time,
                status=ServiceStatus.DEPLOYING,
                inputs=inputs,
                gcp_id=gcp_id,
                aws_arn=aws_arn,
                service_url=service_url,
                docker_image=docker_image,
            )

            # Handle all exceptions to ensure we commit the service state properly
            try:
                # Save intermediate service state to push status to the backend
                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )

                # NOTE: Plans are returned in the same order as they are passed in
                to_execute_plans: List[Plan] = []
                if self.build_service_plan is not None:
                    to_execute_plans.append(self.build_service_plan)
                to_execute_plans.append(self.release_service_plan)
                results = await execute_plans(to_execute_plans, tree)

                build_service_result: Optional[BuildServiceResult] = None
                if self.build_service_plan is not None:
                    build_service_result = results[0]  # type: ignore
                    release_service_result: ReleaseServiceResult = results[1]  # type: ignore
                else:
                    release_service_result: ReleaseServiceResult = results[0]  # type: ignore
                deploy_successful = all(result.success for result in results)

                if build_service_result is not None:
                    new_service_state.docker_image = build_service_result.docker_image
                new_service_state.service_url = release_service_result.service_url
                if deploy_successful:
                    new_service_state.status = ServiceStatus.READY
                    # NOTE: We dont save the inputs until the deploy is successful
                    new_service_state.inputs = self.service.inputs().to_dict()
                else:
                    new_service_state.status = ServiceStatus.DEPLOY_FAILED

                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )

                return DeployServiceResult(
                    self,
                    deploy_successful,
                    new_service_state,
                    build_service_result,
                    release_service_result,
                )
            except Exception as e:
                logging.error(
                    "Exception occurred while deploying service %s: %s",
                    self.service.name,
                    e,
                    exc_info=True,
                )
                # If an exception occurs we save the service state with a failed status
                new_service_state.status = ServiceStatus.DEPLOY_FAILED
                await self.service_manager.save_service(
                    new_service_state, lock_info.lock_id
                )
                build_service_result = None
                if self.build_service_plan is not None:
                    build_service_result = await self.build_service_plan.abandon_plan(
                        "Unknown error occurred while deploying service"
                    )
                release_service_result = await self.release_service_plan.abandon_plan(
                    "Unknown error occurred while deploying service"
                )
                result = DeployServiceResult(
                    self,
                    False,
                    new_service_state,
                    build_service_result,
                    release_service_result,
                )
                result.error_message = str(e)
                return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        left_padding_str = " " * left_padding
        console.print(
            f"{left_padding_str}{ServiceRef(self.service)} will be [{OP_COLOR}]deployed[/{OP_COLOR}] with the following workflow:"
        )
        step_number = 1
        if self.build_service_plan is not None:
            step_number = 2
            self.build_service_plan.print_plan(console, left_padding=left_padding + 4)
        self.release_service_plan.print_plan(
            console, left_padding=left_padding + 4, step_number=step_number
        )

    def task_description(self):
        return f"Deploying {ServiceRef(self.service)}..."

    def success_message(self):
        return f"Successfully deployed {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to deploy {ServiceRef(self.service)}"

    def pending_message(self):
        return f"Deploy {ServiceRef(self.service)} waiting for create operations to finish..."

    async def lock_plan(self) -> Lock:
        if self._lock is not None:
            raise exceptions.PlanAlreadyLocked(self)

        op_type = OperationType.DEPLOY_SERVICE
        plan_output = io.StringIO()
        console = Console(no_color=True, file=plan_output)
        self.print_plan(console)
        plan_output.seek(0)

        lock = await self.service_manager.lock_service(
            operation=LockOperation(
                operation_type=op_type, metadata={"plan": plan_output.read()}
            ),
        )

        try:
            refreshed_service_state = await self.service_manager.load_service()
        except exceptions.ServiceNotFound:
            refreshed_service_state = None

        # NOTE: The refreshed service state will usually be different since create ops
        # will have just executed. We only check if deploy-related fields have changed.
        def _service_state_differs(
            a: Optional[ServiceState], b: Optional[ServiceState]
        ) -> bool:
            # TODO: think through the edge cases here with null states.
            # Maybe we should throw an error if the service state is not Ready?
            if a is None or b is None:
                return False
            return (
                a.product != b.product
                # or a.service_url != b.service_url
                or a.docker_image != b.docker_image
            )

        if _service_state_differs(self.existing_service_state, refreshed_service_state):
            # If the service has changed since planning we release the lock and will not
            # attempt to execute the plan
            await lock.release(reason=ReleaseReason.ABANDONED)
            raise exceptions.ServiceStateMismatch(self.service)

        # NOTE: We override the existing service state with the refreshed state
        # so we cna pull in things like gcp_id and aws_arn from the create step
        self.existing_service_state = refreshed_service_state

        self._lock = lock
        return lock


async def plan_deploy_service(
    service: Service,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
    build_local: bool,
    skip_build: bool,
) -> Union[DeployServicePlan, FailedToPlan]:
    try:
        validate_service_name(service.name)
    except ValueError as e:
        return FailedToPlan(
            service=service,
            error_message=str(e),
        )

    if service.cloud_provider() == CloudProvider.GCP:
        if environment_state.gcp_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use a GCP Service in an AWS Environment.",
            )
    elif service.cloud_provider() == CloudProvider.AWS:
        if environment_state.aws_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use an AWS Service in a GCP Environment.",
            )

    service_manager = environment_manager.create_service_manager(service.name)
    try:
        existing_service = await service_manager.load_service()
    except exceptions.ServiceNotFound:
        existing_service = None

    if existing_service is not None and existing_service.product != service.product:
        exception = exceptions.ServiceProductMismatch(
            service=service,
            existing_product=existing_service.product,
            new_product=service.product,
        )
        return FailedToPlan(
            service=service,
            error_message=str(exception),
        )

    # TODO: Rethink how we generate deployment ids
    deployment_id = generate_deployment_id()

    # Plan the build for the service
    build_plan = None
    if not skip_build:
        build_plan = BuildServicePlan(
            resource_or_service=service,
            service_manager=service_manager,
            environment_state=environment_state,
            deployment_id=deployment_id,
            depends_on=[],
            verbose=verbose,
            build_local=build_local,
        )
    else:
        if existing_service is None:
            return FailedToPlan(
                service=service,
                error_message="Cannot deploy a service with the `--skip-build` flag if the service does not exist. Ensure you have run `lf deploy` without the --skip-build flag first.",
            )
        if existing_service.docker_image is None:
            return FailedToPlan(
                service=service,
                error_message="Cannot deploy a service without a docker image. Ensure you have run `lf deploy` without the --skip-build flag first.",
            )

    # Plan the release for the service
    depends_on: List[Plan] = []
    docker_step: Optional[Literal["build"]] = None
    if build_plan is not None:
        depends_on = [build_plan]
        docker_step = "build"
    release_plan = ReleaseServicePlan(
        resource_or_service=service,
        depends_on=depends_on,
        verbose=verbose,
        environment_ref=EnvironmentRef(environment_manager, show_backend=False),
        service_manager=service_manager,
        environment_state=environment_state,
        deployment_id=deployment_id,
        build_step_type=docker_step,
    )

    return DeployServicePlan(
        resource_or_service=service,
        service_manager=service_manager,
        existing_service_state=existing_service,
        build_service_plan=build_plan,
        release_service_plan=release_plan,
        depends_on=[],
        verbose=verbose,
    )


async def plan_deploy(
    *nodes: Node,
    environment_state: EnvironmentState,
    environment_manager: EnvironmentManager,
    verbose: bool,
    build_local: bool,
    skip_create: bool,
    skip_build: bool,
) -> List[
    Union[CreateResourcePlan, CreateServicePlan, DeployServicePlan, FailedToPlan]
]:
    resource_nodes: List[Resource] = []
    service_nodes: List[Service] = []
    for node in nodes:
        if isinstance(node, Resource):
            resource_nodes.append(node)
        elif isinstance(node, Service):
            service_nodes.append(node)
        else:
            raise ValueError(f"Unknown node type {node}")

    create_plans = []
    if not skip_create:
        create_plans = await plan_create(
            *resource_nodes,
            *service_nodes,
            environment_state=environment_state,
            environment_manager=environment_manager,
            verbose=verbose,
        )

    deploy_service_plans = await asyncio.gather(
        *[
            plan_deploy_service(
                service=service,
                environment_state=environment_state,
                environment_manager=environment_manager,
                verbose=verbose,
                build_local=build_local,
                skip_build=skip_build,
            )
            for service in service_nodes
        ]
    )
    # We need to check if the skip create flag will cause the deploy to fail.
    # If so, we swap it for a FailedToPlan.
    if skip_create:
        keyed_deploy_service_plans = {
            plan.service.name: plan  # type: ignore
            for plan in deploy_service_plans  # type: ignore
        }
        create_service_plans = await asyncio.gather(
            *[
                plan_create_service(
                    service=service,
                    environment_state=environment_state,
                    environment_manager=environment_manager,
                    verbose=verbose,
                    parent_resource_plans={},
                )
                for service in service_nodes
            ]
        )
        for plan in create_service_plans:
            if isinstance(plan, FailedToPlan) or plan.operation_type != "noop":  # type: ignore
                keyed_deploy_service_plans[plan.service.name] = FailedToPlan(  # type: ignore
                    service=plan.service,
                    error_message="Cannot deploy service without creating it. Try again without the --skip-create flag.",
                )
        deploy_service_plans = list(keyed_deploy_service_plans.values())

    return create_plans + deploy_service_plans  # type: ignore


def _find_services_without_dockerfiles(
    nodes: Tuple[Node],
):
    services_without_dockerfile = []
    for node in nodes:
        if isinstance(node, DockerService):
            if not os.path.exists(node.dockerfile):
                services_without_dockerfile.append(node)
    return services_without_dockerfile


async def deploy(
    *nodes: Tuple[Node],
    environment: str,
    prompt: bool = True,
    verbose: bool = False,
    build_local: bool = False,
    skip_create: bool = False,
    check_dockerfiles: bool = False,
    skip_build: bool = False,
    console: Console = Console(),
) -> FlowResult:
    """
    Create resources and deploy services in an environment.

    Args:
    - `nodes`: A tuple of Resources and Services to create.
    - `environment`: The name of the environment to create resources in. Defaults
        to the env configured in the launchflow.yaml.
    - `prompt`: Whether to prompt the user before creating resources.
    - `verbose`: If true all logs will be written to stdout.
    """
    if not nodes:
        if skip_create:
            console.print("No services to deploy. Exiting.")
        else:
            console.print("No resources to create or services to deploy. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    if build_local and not docker_service_available():
        console.print(
            "Docker must be installed to use the --build-local flag. Exiting."
        )
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    if launchflow.project is None:
        console.print("Could not determine the project. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    environment_manager = EnvironmentManager(
        project_name=launchflow.project,
        environment_name=environment,  # type: ignore
        backend=config.launchflow_yaml.backend,
    )

    environment_state = await environment_manager.load_environment()
    if environment_state.status == EnvironmentStatus.CREATE_FAILED:
        raise exceptions.EnvironmentInFailedCreateState(environment)

    if not skip_build and check_dockerfiles:
        services_without_dockerfile = _find_services_without_dockerfiles(nodes)  # type: ignore
        if services_without_dockerfile:
            console.print(
                "[yellow]The following services need a Dockerfile before they can be deployed:[/yellow]"
            )
            for service in services_without_dockerfile:
                console.print(f"  - {ServiceRef(service)}")
            console.print()
            if not prompt:
                console.print(
                    "Rerun this command without the --auto-approve or -y flags to be prompted to generate the Dockerfiles."
                )
                return FlowResult(success=False, plan_results=[], failed_plans=[])
            else:
                gcp_or_aws = "gcp" if environment_state.gcp_config else "aws"
                for service in services_without_dockerfile:
                    created = generate_dockerfile(service, gcp_or_aws, console)  # type: ignore
                    if not created:
                        console.print(
                            f"Dockerfile not created for {ServiceRef(service)}. Exiting."
                        )
                        return FlowResult(
                            success=False, plan_results=[], failed_plans=[]
                        )

    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Planning infrastructure changes...\n", total=None)

        # Step 1: Build the plans
        plans = await plan_deploy(
            *nodes,  # type: ignore
            environment_state=environment_state,
            environment_manager=environment_manager,
            verbose=verbose,
            build_local=build_local,
            skip_create=skip_create,
            skip_build=skip_build,
        )

        progress.remove_task(task)

    create_plans: List[Union[CreateResourcePlan, CreateServicePlan]] = []
    deploy_service_plans: List[DeployServicePlan] = []
    failed_plans: List[FailedToPlan] = []
    for plan in plans:
        if isinstance(plan, CreateResourcePlan) or isinstance(plan, CreateServicePlan):
            create_plans.append(plan)
        elif isinstance(plan, DeployServicePlan):
            deploy_service_plans.append(plan)
        elif isinstance(plan, FailedToPlan):
            failed_plans.append(plan)

    # dedupe the failed plans since a failed create service plan is a failed deploy service plan
    keyed_plans = {str(plan.reference()): plan for plan in failed_plans}
    failed_plans = list(keyed_plans.values())

    # TODO: Do a stumble to determine if we should prompt the create + deploy plans
    # together or separately. Separately has less gotchas, but feels a bit clunky.
    # Step 2: Select the plans
    print_plans(
        *plans,
        environment_manager=environment_manager,
        console=console,
    )
    service_names_that_need_create = set(
        [
            plan.service.name  # type: ignore
            for plan in create_plans + failed_plans
            if (isinstance(plan, CreateServicePlan) and plan.operation_type == "create")
            or (isinstance(plan, FailedToPlan) and plan.service is not None)
        ]
    )
    selected_create_plans: Union[
        None, List[Union[CreateResourcePlan, CreateServicePlan]]
    ] = await select_plans(  # type: ignore
        *create_plans,
        operation_type="create",
        environment_manager=environment_manager,
        console=console,
        confirm=prompt,
    )
    if selected_create_plans is None:
        selected_create_service_names = set()
    else:
        selected_create_service_names = set(
            [
                plan.service.name
                for plan in selected_create_plans
                if isinstance(plan, CreateServicePlan)
                and plan.operation_type == "create"
            ]
        )
    serivce_names_that_will_fail_to_deploy = (
        service_names_that_need_create - selected_create_service_names
    )
    if serivce_names_that_will_fail_to_deploy:
        removed_deploy_plans: List[DeployServicePlan] = []
        new_deploy_service_plans: List[DeployServicePlan] = []
        for plan in deploy_service_plans:
            if plan.service.name in serivce_names_that_will_fail_to_deploy:
                removed_deploy_plans.append(plan)
            else:
                new_deploy_service_plans.append(plan)
        deploy_service_plans = new_deploy_service_plans

        if removed_deploy_plans:
            console.print(
                "[yellow]The following services need to be created before they can be deployed:[/yellow]"
            )
            for plan in removed_deploy_plans:
                console.print(f"  - {ServiceRef(plan.service)}")
            console.print()

    selected_deploy_plans: Union[None, List[DeployServicePlan]] = await select_plans(  # type: ignore
        *deploy_service_plans,
        operation_type="deploy",
        environment_manager=environment_manager,
        console=console,
        confirm=prompt,
    )

    # The None is a special case for no valid plans
    if selected_create_plans is None and selected_deploy_plans is None:
        if skip_create:
            console.print("No services to deploy. Exiting.")
        else:
            console.print("Nothing to create or deploy. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=failed_plans)

    # The empty list case means the user did not confirm any plans
    # We only check the deploy plans
    if not selected_deploy_plans:
        console.print("No deploy plans selected. Exiting.")
        return FlowResult(success=True, plan_results=[], failed_plans=failed_plans)

    if selected_create_plans is None:
        selected_create_plans = []
    if selected_deploy_plans is None:
        selected_deploy_plans = []

    # Step 3: Lock the plans
    # TODO: Determine if we should check if the Environment state has changed since planning
    if selected_create_plans:
        async with lock_plans(
            *selected_create_plans, environment_manager=environment_manager
        ):
            # Step 4: Execute the plans
            console.rule("[bold purple]create operations")

            tree = Tree(
                "Plans",
                guide_style=Style(dim=True),
                hide_root=True,
            )
            with Live(
                Padding(tree, (1, 0, 1, 0)), console=console, refresh_per_second=8
            ):
                create_results: List[
                    Union[CreateResourceResult, CreateServiceResult]
                ] = await execute_plans(
                    selected_create_plans,  # type: ignore
                    tree,  # type: ignore
                )  # type: ignore
    else:
        create_results = []

    create_has_failures = any(not result.success for result in create_results)
    deploy_results: List[DeployServiceResult] = []
    if create_has_failures:
        console.rule("[bold purple]deploy operations")
        console.print(
            "\n[yellow]Skipping deploy operations due to create failures[/yellow]\n"
        )
    else:
        async with lock_plans(
            *selected_deploy_plans, environment_manager=environment_manager
        ):
            # Step 4: Execute the plans
            console.rule("[bold purple]deploy operations")

            tree = Tree(
                "Plans",
                guide_style=Style(dim=True),
                hide_root=True,
            )
            with Live(
                Padding(tree, (1, 0, 1, 0)), console=console, refresh_per_second=8
            ):
                deploy_results.extend(
                    await execute_plans(selected_deploy_plans, tree)  # type: ignore
                )

    # TODO: Move the print logic below to a shared utility that takes in a FlowResult
    success = all(result.success for result in create_results + deploy_results)
    flow_result = FlowResult(
        success=success,
        plan_results=create_results + deploy_results,  # type: ignore
        failed_plans=failed_plans,
    )

    # Step 5: Print the results

    # Step 5.1: Print the logs
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Operation", justify="left", no_wrap=False)
    table.add_column("Logs", style="blue", overflow="fold")
    # Add the logs for the create resource results
    if create_results:
        for result in create_results:
            if isinstance(result, CreateResourceResult):
                if result.logs_file is None:
                    continue

                log_link_line = result.logs_file
                if log_link_line.startswith("http"):
                    log_link_line = f"[link={log_link_line}]{log_link_line}[/link]"

                if result.success:
                    table.add_row(
                        f"[green]✓[/green] {result.plan.operation_type.title()} {result.plan.reference()}",
                        log_link_line,
                    )
                else:
                    table.add_row(
                        f"[red]✗[/red] {result.plan.operation_type.title()} {result.plan.reference()}",
                        log_link_line,
                    )
            elif isinstance(result, CreateServiceResult):
                for resource_result in result.create_resource_results:
                    if resource_result.logs_file is None:
                        continue

                    if resource_result.success:
                        table.add_row(
                            f"[green]✓[/green] {resource_result.plan.operation_type.title()} {resource_result.plan.reference()}",
                            resource_result.logs_file,
                        )
                    else:
                        table.add_row(
                            f"[red]✗[/red] {resource_result.plan.operation_type.title()} {resource_result.plan.reference()}",
                            resource_result.logs_file,
                        )
    # Add the logs for the deploy service results
    if deploy_results:
        for result in deploy_results:  # type: ignore
            # Logs for service build step
            if result.build_result is not None:  # type: ignore
                if result.build_result.logs_file_or_link is None:  # type: ignore
                    continue

                if result.success:
                    table.add_row(
                        f"[green]✓[/green] {result.plan.build_service_plan.operation_type.title()} {result.plan.build_service_plan.reference()}",  # type: ignore
                        result.build_result.logs_file_or_link,  # type: ignore
                    )
                else:
                    table.add_row(
                        f"[red]✗[/red] {result.plan.build_service_plan.operation_type.title()} {result.plan.build_service_plan.reference()}",  # type: ignore
                        result.build_result.logs_file_or_link,  # type: ignore
                    )

    # We only print the logs table if there are logs to show
    if table.row_count > 0:
        console.rule("[bold purple]logs")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # Step 5.2: Print the service urls
    table = Table(
        show_header=True,
        show_edge=False,
        show_lines=False,
        box=None,
        padding=(0, 1),
    )
    table.add_column("Service", justify="left", no_wrap=True)
    table.add_column("URL", style="blue", overflow="fold")
    for result in deploy_results:  # type: ignore
        # This is None when the plan was abandoned
        if (
            result.service_state is not None  # type: ignore
            and result.service_state.service_url is not None  # type: ignore
        ):
            table.add_row(
                str(ServiceRef(result.plan.service)),  # type: ignore
                result.service_state.service_url,  # type: ignore
            )

    # We only print the service urls table if there are urls to show
    if table.row_count > 0:
        console.rule("[bold purple]service urls")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # Step 5.3: Print the dns settings
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Service", justify="left", no_wrap=True)
    table.add_column("Host name", style="light_cyan3", overflow="fold")
    table.add_column("Type", style="yellow3", overflow="fold")
    table.add_column("IP Address", style="pale_green3", overflow="fold")
    for result in create_results:
        if isinstance(result, CreateServiceResult) and result.dns_outputs is not None:
            for record in result.dns_outputs.dns_records:
                table.add_row(
                    str(ServiceRef(result.plan.service)),
                    result.dns_outputs.domain,
                    record.dns_record_type,
                    record.dns_record_value,
                )
    if table.row_count > 0:
        console.rule("[bold purple]custom domains")
        console.print("Add or update these records in your DNS settings:\n")
        console.print(table, overflow="fold")
        console.print()

    # Step 5.4: Print the secrets
    secrets: List[Resource] = []
    for result in create_results:
        if (
            isinstance(result, CreateResourceResult)
            and is_secret_resource(result.plan.resource)
            and result.success
        ):
            secrets.append(result.plan.resource)
    if secrets:
        console.rule("[bold purple]secrets")
        console.print("Run these commands to set the value of your secrets:\n")
        for secret in secrets:
            console.print(f"{ResourceRef(secret)}:")
            console.print(
                f"    $ lf secrets set --environment={environment} {secret.name} some-value"
            )
            console.print()

    # Step 5.5: Print the results summary
    console.rule("[bold purple]summary")
    console.print()

    successful_resource_create_count = 0
    failed_resource_create_count = 0
    successful_resource_update_count = 0
    failed_resource_update_count = 0
    successful_resource_replace_count = 0
    failed_resource_replace_count = 0
    successful_service_create_count = 0
    failed_service_create_count = 0
    successful_service_update_count = 0
    failed_service_update_count = 0
    successful_service_deploy_count = 0
    failed_service_deploy_count = 0

    for result in create_results + deploy_results:  # type: ignore
        if isinstance(result, CreateResourceResult):
            if result.success:
                if result.plan.operation_type == "create":
                    successful_resource_create_count += 1
                elif result.plan.operation_type == "update":
                    successful_resource_update_count += 1
                elif result.plan.operation_type == "replace":
                    successful_resource_replace_count += 1
            else:
                if result.plan.operation_type == "create":
                    failed_resource_create_count += 1
                elif result.plan.operation_type == "update":
                    failed_resource_update_count += 1
                elif result.plan.operation_type == "replace":
                    failed_resource_replace_count += 1

        if isinstance(result, CreateServiceResult):
            if result.success:
                successful_service_create_count += 1
            else:
                failed_service_create_count += 1
            for resource_result in result.create_resource_results:
                if resource_result.success:
                    if resource_result.plan.operation_type == "create":
                        successful_resource_create_count += 1
                    elif resource_result.plan.operation_type == "update":
                        successful_resource_update_count += 1
                    elif resource_result.plan.operation_type == "replace":
                        successful_resource_replace_count += 1
                else:
                    if resource_result.plan.operation_type == "create":
                        failed_resource_create_count += 1
                    elif resource_result.plan.operation_type == "update":
                        failed_resource_update_count += 1
                    elif resource_result.plan.operation_type == "replace":
                        failed_resource_replace_count += 1

        elif isinstance(result, DeployServiceResult):
            if result.success:
                successful_service_deploy_count += 1
            else:
                failed_service_deploy_count += 1

    if successful_resource_create_count or successful_service_create_count:
        if successful_service_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'} and {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
    if failed_resource_create_count or failed_service_create_count:
        if failed_service_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'} and {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
    if successful_resource_update_count or successful_service_update_count:
        if successful_service_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'} and {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
    if failed_resource_update_count or failed_service_update_count:
        if failed_service_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'} and {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
    if successful_resource_replace_count:
        console.print(
            f"[green]Successfully replaced {successful_resource_replace_count} {'resource' if successful_resource_replace_count == 1 else 'resources'}[/green]"
        )
    if failed_resource_replace_count:
        console.print(
            f"[red]Failed to replace {failed_resource_replace_count} {'resource' if failed_resource_replace_count == 1 else 'resources'}[/red]"
        )
    if successful_service_deploy_count:
        console.print(
            f"[green]Successfully deployed {successful_service_deploy_count} {'service' if successful_service_deploy_count == 1 else 'services'}[/green]"
        )
    if failed_service_deploy_count:
        console.print(
            f"[red]Failed to deploy {failed_service_deploy_count} {'service' if failed_service_deploy_count == 1 else 'services'}[/red]"
        )

    if create_has_failures:
        num_deployments_skipped = len(selected_deploy_plans)
        console.print(
            f"[yellow]Skipped {num_deployments_skipped} {'deployment' if num_deployments_skipped == 1 else 'deployments'} due to create failures[/yellow]"
        )

    console.print()

    return flow_result


@dataclasses.dataclass
class PromoteDockerImageResult(Result["PromoteDockerImagePlan"]):
    docker_image: Optional[str] = None
    logs_file_or_link: Optional[str] = None


# TODO: Make the Promote plan more generic so its not specific to Docker
@dataclasses.dataclass
class PromoteDockerImagePlan(ServicePlan):
    from_service_state: ServiceState
    from_gcp_environment_config: Optional[GCPEnvironmentConfig]
    to_gcp_environment_config: Optional[GCPEnvironmentConfig]
    from_aws_environment_config: Optional[AWSEnvironmentConfig]
    to_aws_environment_config: Optional[AWSEnvironmentConfig]
    to_environment_ref: EnvironmentRef
    deployment_id: str
    promote_local: bool

    # TODO: add a local promotion option
    # promote_local: bool = False

    def __post_init__(self):
        if (
            self.from_gcp_environment_config is None
            and self.from_aws_environment_config is None
        ):
            raise ValueError(
                "GCP or AWS environment config must be provided to build a service."
            )
        if isinstance(self.service, GCPService) and (
            self.from_gcp_environment_config is None
            or self.to_gcp_environment_config is None
        ):
            raise ValueError(
                "GCP environment config must be provided to build a GCP service."
            )
        if isinstance(self.service, AWSService) and (
            self.from_aws_environment_config is None
            or self.to_aws_environment_config is None
        ):
            raise ValueError(
                "AWS environment config must be provided to build an AWS service."
            )

    @property
    def operation_type(self) -> Literal["promote"]:
        return "promote"

    async def abandon_plan(self, reason: str):
        result = PromoteDockerImageResult(plan=self, success=False)
        result.error_message = f"Promote Docker image abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> PromoteDockerImageResult:
        try:
            logs_file_or_link = None
            if isinstance(self.service, GCPDockerService):
                docker_image, logs_file_or_link = await promote_gcp_service_image(
                    self.service,
                    from_service_state=self.from_service_state,
                    from_gcp_environment_config=self.from_gcp_environment_config,  # type: ignore
                    to_gcp_environment_config=self.to_gcp_environment_config,  # type: ignore
                    deployment_id=self.deployment_id,
                    promote_local=self.promote_local,
                )
                return PromoteDockerImageResult(
                    self, True, docker_image, logs_file_or_link
                )
            elif isinstance(self.service, AWSService):
                raise NotImplementedError("AWS service promotion is not yet supported.")
            else:
                result = PromoteDockerImageResult(self, False)
                result.error_message = f"Unsupported service type: {self.service}"
                return result
        except exceptions.ServicePromoteFailed as e:
            result = PromoteDockerImageResult(
                self, False, logs_file_or_link=e.promote_logs_or_link
            )
            result.error_message = str(e)
            return result
        except Exception as e:
            # TODO: Improve this error handling
            logging.error("Exception occurred: %s", e, exc_info=True)
            result = PromoteDockerImageResult(self, False)
            result.error_message = str(e)
            return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        left_padding_str = " " * left_padding
        console.print()
        console.print(
            f"{left_padding_str}1. {ServiceRef(self.service)} will be [{OP_COLOR}]promoted[/{OP_COLOR}] to {self.to_environment_ref}"
        )
        # TODO: Add a way to fetch the promote diff args based on the deployment id
        # if self.service.promote_diff_args:
        #     promote_inputs_str = format_configuration_dict(
        #         self.service.promote_diff_args
        #     )
        #     console.print()
        #     console.print(
        #         f"{left_padding_str}1. {ServiceRef(self.service)} will be [{OP_COLOR}]promoted[/{OP_COLOR}] with the following configuration:"
        #     )
        #     console.print(
        #         left_padding_str
        #         + "    "
        #         + f"\n{left_padding_str}    ".join(promote_inputs_str.split("\n"))
        #     )

    async def lock_plan(self) -> None:
        return None

    def pending_message(self):
        return f"Promote Docker image for {ServiceRef(self.service)} waiting for dependencies..."

    def task_description(self):
        return f"Promoting Docker image for {ServiceRef(self.service)}..."

    def success_message(self):
        return f"Successfully promoted Docker image for {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to promote Docker image for {ServiceRef(self.service)}"


@dataclasses.dataclass
class PromoteServiceResult(Result["PromoteServicePlan"]):
    service_state: Optional[ServiceState]
    promote_image_result: PromoteDockerImageResult
    release_result: ReleaseServiceResult


@dataclasses.dataclass
class PromoteServicePlan(ServicePlan):
    from_service_manager: ServiceManager
    to_service_manager: ServiceManager
    existing_from_service_state: ServiceState
    existing_to_service_state: Optional[ServiceState]
    promote_docker_image_plan: PromoteDockerImagePlan
    release_service_plan: ReleaseServicePlan
    _lock: Optional[Lock] = None

    def child_plans(self) -> List[Plan]:
        return [self.promote_docker_image_plan, self.release_service_plan]

    @property
    def operation_type(self) -> Literal["promote"]:
        return "promote"

    async def abandon_plan(self, reason: str):
        if self._lock is not None:
            await self._lock.release(ReleaseReason.ABANDONED)

        docker_coro = self.promote_docker_image_plan.abandon_plan(reason)
        abandon_coro = self.release_service_plan.abandon_plan(reason)
        results = await asyncio.gather(docker_coro, abandon_coro)

        result = PromoteServiceResult(self, False, None, results[0], results[1])
        result.error_message = f"Promote abandoned: {reason}"
        return result

    async def execute_plan(
        self,
        tree: Tree,
        dependency_results: List[Result],
    ) -> PromoteServiceResult:
        if self._lock is None:
            return await self.abandon_plan("Plan was not locked before execution.")
        try:
            self.service.outputs()
        except exceptions.ServiceOutputsNotFound:
            return await self.abandon_plan(
                f"Service outputs not found. Ensure you have run: `lf create {self.to_service_manager.environment_name} --service={self.to_service_manager.service_name}`"
            )

        async with self._lock as lock_info:
            updated_time = datetime.datetime.now(datetime.timezone.utc)
            if self.existing_to_service_state:
                created_time = self.existing_to_service_state.created_at
                inputs = self.existing_to_service_state.inputs
                gcp_id = self.existing_to_service_state.gcp_id
                aws_arn = self.existing_to_service_state.aws_arn
                service_url = self.existing_to_service_state.service_url
                docker_image = self.existing_to_service_state.docker_image

            else:
                created_time = updated_time
                # NOTE: We dont save the inputs until the promote is successful
                inputs = None
                gcp_id = None
                aws_arn = None
                service_url = None
                docker_image = None

            new_to_service_state = ServiceState(
                name=self.service.name,
                product=self.service.product,
                cloud_provider=self.service.cloud_provider(),
                created_at=created_time,
                updated_at=updated_time,
                status=ServiceStatus.PROMOTING,
                inputs=inputs,
                gcp_id=gcp_id,
                aws_arn=aws_arn,
                docker_image=docker_image,
                service_url=service_url,
            )

            # Handle all exceptions to ensure we commit the service state properly
            try:
                # Save intermediate service state to push status to the backend
                await self.to_service_manager.save_service(
                    new_to_service_state, lock_info.lock_id
                )

                # NOTE: Plans are returned in the same order as they are passed in
                results = await execute_plans(
                    [
                        self.promote_docker_image_plan,
                        self.release_service_plan,
                    ],
                    tree,
                )

                promote_docker_image_result, release_service_result = results  # type: ignore

                # We do this for type hinting purposes
                promote_docker_image_result: PromoteDockerImageResult = (  # type: ignore
                    promote_docker_image_result
                )
                release_service_result: ReleaseServiceResult = release_service_result  # type: ignore
                deploy_successful = all(result.success for result in results)

                new_to_service_state.docker_image = (
                    promote_docker_image_result.docker_image  # type: ignore
                )
                new_to_service_state.service_url = release_service_result.service_url  # type: ignore
                if deploy_successful:
                    new_to_service_state.status = ServiceStatus.READY
                    # NOTE: We dont save the inputs until the deploy is successful
                    new_to_service_state.inputs = self.service.inputs().to_dict()
                else:
                    new_to_service_state.status = ServiceStatus.PROMOTE_FAILED

                await self.to_service_manager.save_service(
                    new_to_service_state, lock_info.lock_id
                )

                return PromoteServiceResult(
                    self,
                    deploy_successful,
                    new_to_service_state,
                    promote_docker_image_result,  # type: ignore
                    release_service_result,  # type: ignore
                )
            except Exception as e:
                logging.error(
                    "Exception occurred while promoting service %s: %s",
                    self.service.name,
                    e,
                    exc_info=True,
                )
                # If an exception occurs we save the service state with a failed status
                new_to_service_state.status = ServiceStatus.PROMOTE_FAILED
                await self.to_service_manager.save_service(
                    new_to_service_state, lock_info.lock_id
                )
                promote_docker_image_result = (
                    await self.promote_docker_image_plan.abandon_plan(
                        "Unknown error occurred while promoting service"
                    )
                )
                release_service_result = await self.release_service_plan.abandon_plan(
                    "Unknown error occurred while promoting service"
                )
                result = PromoteServiceResult(
                    self,
                    False,
                    new_to_service_state,
                    promote_docker_image_result,  # type: ignore
                    release_service_result,  # type: ignore
                )
                result.error_message = str(e)
                return result

    def print_plan(
        self,
        console: rich.console.Console = rich.console.Console(),
        left_padding: int = 0,
    ):
        service_inputs = self.service.inputs().to_dict()
        left_padding_str = " " * left_padding
        base_msg = f"{left_padding_str}{ServiceRef(self.service)} will be [{OP_COLOR}]promoted[/{OP_COLOR}] from {EnvironmentRef(self.from_service_manager, show_backend=False)} to {EnvironmentRef(self.to_service_manager, show_backend=False)} with the following workflow:"
        if service_inputs:
            pretty_inputs = format_configuration_dict(service_inputs)
            pretty_inputs = f"\n{left_padding_str}    ".join(pretty_inputs.split("\n"))
            base_msg += f" With the following configuration:\n{left_padding_str}    {pretty_inputs}"
        console.print(base_msg)
        self.promote_docker_image_plan.print_plan(
            console, left_padding=left_padding + 4
        )
        self.release_service_plan.print_plan(console, left_padding=left_padding + 4)

    def task_description(self):
        return f"Promoting {ServiceRef(self.service)}..."

    def success_message(self):
        return f"Successfully promoted {ServiceRef(self.service)}"

    def failure_message(self):
        return f"Failed to promote {ServiceRef(self.service)}"

    def pending_message(self):
        return f"Promote {ServiceRef(self.service)} waiting for dependencies..."

    async def lock_plan(self) -> Lock:
        if self._lock is not None:
            raise exceptions.PlanAlreadyLocked(self)

        op_type = OperationType.PROMOTE_SERVICE
        plan_output = io.StringIO()
        console = Console(no_color=True, file=plan_output)
        self.print_plan(console)
        plan_output.seek(0)

        lock = await self.to_service_manager.lock_service(
            operation=LockOperation(
                operation_type=op_type, metadata={"plan": plan_output.read()}
            ),
        )

        try:
            refreshed_service_state = await self.to_service_manager.load_service()
        except exceptions.ServiceNotFound:
            refreshed_service_state = None

        # NOTE: The refreshed service state will usually be different since create ops
        # will have just executed. We only check if deploy-related fields have changed.
        def _service_state_differs(
            a: Optional[ServiceState], b: Optional[ServiceState]
        ) -> bool:
            # TODO: think through the edge cases here with null states.
            # Maybe we should throw an error if the service state is not Ready?
            if a is None or b is None:
                return False
            return (
                a.product != b.product
                or a.service_url != b.service_url
                or a.docker_image != b.docker_image
            )

        if _service_state_differs(
            self.existing_to_service_state, refreshed_service_state
        ):
            # If the service has changed since planning we release the lock and will not
            # attempt to execute the plan
            await lock.release(reason=ReleaseReason.ABANDONED)
            raise exceptions.ServiceStateMismatch(self.service)

        self._lock = lock
        return lock


async def plan_promote_service(
    service: Service,
    from_environment_state: EnvironmentState,
    to_environment_state: EnvironmentState,
    from_environment_manager: EnvironmentManager,
    to_environment_manager: EnvironmentManager,
    verbose: bool,
    promote_local: bool,
) -> Union[PromoteServicePlan, FailedToPlan]:
    try:
        validate_service_name(service.name)
    except ValueError as e:
        return FailedToPlan(
            service=service,
            error_message=str(e),
        )

    if service.cloud_provider() == CloudProvider.GCP:
        if to_environment_state.gcp_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use a GCP Service in an AWS Environment.",
            )
    elif service.cloud_provider() == CloudProvider.AWS:
        if to_environment_state.aws_config is None:
            return FailedToPlan(
                service=service,
                error_message="CloudProviderMismatch: Cannot use an AWS Service in a GCP Environment.",
            )

    to_service_manager = to_environment_manager.create_service_manager(service.name)
    try:
        existing_to_service = await to_service_manager.load_service()
    except exceptions.ServiceNotFound:
        existing_to_service = None

    if (
        existing_to_service is not None
        and existing_to_service.product != service.product
    ):
        exception = exceptions.ServiceProductMismatch(
            service=service,
            existing_product=existing_to_service.product,
            new_product=service.product,
        )
        return FailedToPlan(
            service=service,
            error_message=str(exception),
        )

    from_service_manager = from_environment_manager.create_service_manager(service.name)
    try:
        existing_from_service = await from_service_manager.load_service()
    except exceptions.ServiceNotFound:
        return FailedToPlan(
            service=service,
            error_message="ServiceNotFound: Service does not exist in the source environment.",
        )

    if existing_from_service.product != service.product:
        exception = exceptions.ServiceProductMismatch(
            service=service,
            existing_product=existing_from_service.product,
            new_product=service.product,
        )
        return FailedToPlan(
            service=service,
            error_message=str(exception),
        )

    # TODO: Rethink how we generate deployment ids
    deployment_id = generate_deployment_id()

    # Plan the build for the service
    promote_docker_image_plan = PromoteDockerImagePlan(
        resource_or_service=service,
        depends_on=[],
        verbose=verbose,
        from_service_state=existing_from_service,
        from_gcp_environment_config=from_environment_state.gcp_config,
        to_gcp_environment_config=to_environment_state.gcp_config,
        from_aws_environment_config=from_environment_state.aws_config,
        to_aws_environment_config=to_environment_state.aws_config,
        deployment_id=deployment_id,
        promote_local=promote_local,
        to_environment_ref=EnvironmentRef(to_environment_manager, show_backend=False),
    )

    # Plan the release for the service
    release_plan = ReleaseServicePlan(
        resource_or_service=service,
        depends_on=[promote_docker_image_plan],
        verbose=verbose,
        environment_ref=EnvironmentRef(to_environment_manager, show_backend=False),
        service_manager=to_service_manager,
        environment_state=to_environment_state,
        deployment_id=deployment_id,
        build_step_type="promote",
    )

    return PromoteServicePlan(
        resource_or_service=service,
        depends_on=[],
        verbose=verbose,
        from_service_manager=from_service_manager,
        to_service_manager=to_service_manager,
        existing_from_service_state=existing_from_service,
        existing_to_service_state=existing_to_service,
        promote_docker_image_plan=promote_docker_image_plan,
        release_service_plan=release_plan,
    )


async def plan_promote(
    *nodes: Node,
    from_environment_state: EnvironmentState,
    to_environment_state: EnvironmentState,
    from_environment_manager: EnvironmentManager,
    to_environment_manager: EnvironmentManager,
    verbose: bool,
    promote_local: bool,
) -> List[Union[PromoteServicePlan, FailedToPlan]]:
    resource_nodes: List[Resource] = []
    service_nodes: List[Service] = []
    for node in nodes:
        if isinstance(node, Resource):
            resource_nodes.append(node)
        elif isinstance(node, Service):
            service_nodes.append(node)
        else:
            raise ValueError(f"Unknown node type {node}")

    # TODO: determine if we should create resources in the target environment
    # create_plans = []
    # if not skip_create:
    #     create_plans = await plan_create(
    #         *resource_nodes,
    #         *service_nodes,
    #         environment=environment,
    #         environment_manager=environment_manager,
    #         verbose=verbose,
    #     )

    deploy_service_plans = await asyncio.gather(
        *[
            plan_promote_service(
                service=service,
                from_environment_state=from_environment_state,
                to_environment_state=to_environment_state,
                from_environment_manager=from_environment_manager,
                to_environment_manager=to_environment_manager,
                verbose=verbose,
                promote_local=promote_local,
            )
            for service in service_nodes
        ]
    )
    # We need to check if the skip create flag will cause the deploy to fail.
    # If so, we swap it for a FailedToPlan.
    # if skip_create:
    #     keyed_deploy_service_plans = {
    #         plan.service.name: plan for plan in deploy_service_plans
    #     }
    #     create_service_plans = await asyncio.gather(
    #         *[
    #             plan_create_service(
    #                 service=service,
    #                 environment=environment,
    #                 environment_manager=environment_manager,
    #                 verbose=verbose,
    #             )
    #             for service in service_nodes
    #         ]
    #     )
    #     for plan in create_service_plans:
    #         if isinstance(plan, FailedToPlan) or plan.operation_type != "noop":
    #             keyed_deploy_service_plans[plan.service.name] = FailedToPlan(
    #                 service=plan.service,
    #                 error_message="Cannot deploy service without creating it. Try again without the --skip-create flag.",
    #             )
    #     deploy_service_plans = list(keyed_deploy_service_plans.values())

    return deploy_service_plans


async def promote(
    *nodes: Tuple[Node],
    from_environment: str,
    to_environment: str,
    prompt: bool = True,
    verbose: bool = False,
    promote_local: bool = False,
    console: Console = Console(),
) -> FlowResult:
    """
    Promote services from one environment to another.

    Args:
    - `nodes`: A tuple of Resources and Services to create.
    - `from_environment`: The name of the environment to promote services from.
    - `to_environment`: The name of the environment to promote services to.
    - `prompt`: Whether to prompt the user before creating resources.
    - `verbose`: If true all logs will be written to stdout.
    - `promote_local`: If true the docker image will be moved to the new environment locally instead of on Cloud Build or Code Build.
    - `console`: The console to write output to.
    """
    if not nodes:
        console.print("No services to promote. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    if launchflow.project is None:
        console.print("Could not determine the project. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=[])

    from_environment_manager = EnvironmentManager(
        project_name=launchflow.project,
        environment_name=from_environment,
        backend=config.launchflow_yaml.backend,
    )
    to_environment_manager = EnvironmentManager(
        project_name=launchflow.project,
        environment_name=to_environment,
        backend=config.launchflow_yaml.backend,
    )

    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Planning infrastructure changes...\n", total=None)

        from_environment_state, to_environment_state = await asyncio.gather(
            from_environment_manager.load_environment(),
            to_environment_manager.load_environment(),
        )
        if from_environment_state.status == EnvironmentStatus.CREATE_FAILED:
            raise exceptions.EnvironmentInFailedCreateState(from_environment)
        if to_environment_state.status == EnvironmentStatus.CREATE_FAILED:
            raise exceptions.EnvironmentInFailedCreateState(to_environment)

        # Step 1: Build the plans
        plans = await plan_promote(
            *nodes,  # type: ignore
            from_environment_state=from_environment_state,
            to_environment_state=to_environment_state,
            from_environment_manager=from_environment_manager,
            to_environment_manager=to_environment_manager,
            verbose=verbose,
            promote_local=promote_local,
        )

        progress.remove_task(task)

    promote_service_plans: List[PromoteServicePlan] = []
    failed_plans: List[FailedToPlan] = []
    for plan in plans:
        if isinstance(plan, PromoteServicePlan):
            promote_service_plans.append(plan)
        elif isinstance(plan, FailedToPlan):
            failed_plans.append(plan)

    # Step 2: Select the plans
    print_plans(
        *plans,
        environment_manager=to_environment_manager,
        console=console,
    )

    selected_promote_plans: Union[None, List[PromoteServicePlan]] = await select_plans(  # type: ignore
        *promote_service_plans,
        operation_type="promote",
        environment_manager=to_environment_manager,
        console=console,
        confirm=prompt,
    )

    # The None is a special case for no valid plans
    if selected_promote_plans is None:
        console.print("No services to promote. Exiting.")
        return FlowResult(success=False, plan_results=[], failed_plans=failed_plans)

    # The empty list case means the user did not confirm any plans
    if not selected_promote_plans:
        console.print("No promote plans selected. Exiting.")
        return FlowResult(success=True, plan_results=[], failed_plans=failed_plans)

    # Step 3: Lock the plans
    async with lock_plans(
        *selected_promote_plans, environment_manager=to_environment_manager
    ):
        # Step 4: Execute the plans
        console.rule("[bold purple]operations")

        tree = Tree(
            "Plans",
            guide_style=Style(dim=True),
            hide_root=True,
        )
        with Live(Padding(tree, (1, 0, 1, 0)), console=console, refresh_per_second=8):
            promote_results: List[PromoteServiceResult] = await execute_plans(  # type: ignore
                selected_promote_plans,  # type: ignore
                tree,  # type: ignore
            )

    # TODO: Move the print logic below to a shared utility that takes in a FlowResult
    success = all(result.success for result in promote_results)
    flow_result = FlowResult(  # type: ignore
        success=success,
        plan_results=promote_results,  # type: ignore
        failed_plans=failed_plans,  # type: ignore
    )

    # Step 5: Print the results

    # TODO: move this to a shared utility
    # Step 5.1: Print the logs
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Operation", justify="left", no_wrap=True)
    table.add_column("Logs", style="blue", overflow="fold")

    # Add the logs for the promote service results
    for result in promote_results:
        # Logs for service image promote step
        if result.promote_image_result.logs_file_or_link is None:
            continue

        log_link_line = result.promote_image_result.logs_file_or_link
        if log_link_line.startswith("http"):
            log_link_line = f"[link={log_link_line}]{log_link_line}[/link]"

        if result.success:
            table.add_row(
                f"[green]✓[/green] {result.plan.promote_docker_image_plan.operation_type.title()} {result.plan.promote_docker_image_plan.reference()}",
                log_link_line,
            )
        else:
            table.add_row(
                f"[red]✗[/red] {result.plan.promote_docker_image_plan.operation_type.title()} {result.plan.promote_docker_image_plan.reference()}",
                log_link_line,
            )

    # We only print the logs table if there are logs to show
    if table.row_count > 0:
        console.rule("[bold purple]logs")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # Step 5.2: Print the service urls
    table = Table(
        show_header=True, show_edge=False, show_lines=False, box=None, padding=(0, 1)
    )
    table.add_column("Service", justify="left", no_wrap=True)
    table.add_column("URL", style="blue", overflow="fold")
    for result in promote_results:
        # This is None when the plan was abandoned
        if (
            result.service_state is not None
            and result.service_state.service_url is not None
        ):
            table.add_row(
                str(ServiceRef(result.plan.service)),
                result.service_state.service_url,
            )

    # We only print the service urls table if there are urls to show
    if table.row_count > 0:
        console.rule("[bold purple]service urls")
        console.print()
        console.print(table, overflow="fold")
        console.print()

    # Step 5.3: Print the dns settings
    # TODO: add dns settings section

    # Step 5.4: Print the results summary
    console.rule("[bold purple]summary")
    console.print()

    successful_resource_create_count = 0
    failed_resource_create_count = 0
    successful_resource_update_count = 0
    failed_resource_update_count = 0
    successful_resource_replace_count = 0
    failed_resource_replace_count = 0
    successful_service_create_count = 0
    failed_service_create_count = 0
    successful_service_update_count = 0
    failed_service_update_count = 0
    successful_service_promote_count = 0
    failed_service_promote_count = 0

    for result in promote_results:
        if result.success:
            successful_service_promote_count += 1
        else:
            failed_service_promote_count += 1

    if successful_resource_create_count or successful_service_create_count:
        if successful_service_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_create_count == 0:
            console.print(
                f"[green]Successfully created {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully created {successful_resource_create_count} {'resource' if successful_resource_create_count == 1 else 'resources'} and {successful_service_create_count} {'service' if successful_service_create_count == 1 else 'services'}[/green]"
            )
    if failed_resource_create_count or failed_service_create_count:
        if failed_service_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_create_count == 0:
            console.print(
                f"[red]Failed to create {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to create {failed_resource_create_count} {'resource' if failed_resource_create_count == 1 else 'resources'} and {failed_service_create_count} {'service' if failed_service_create_count == 1 else 'services'}[/red]"
            )
    if successful_resource_update_count or successful_service_update_count:
        if successful_service_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'}[/green]"
            )
        elif successful_resource_update_count == 0:
            console.print(
                f"[green]Successfully updated {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
        else:
            console.print(
                f"[green]Successfully updated {successful_resource_update_count} {'resource' if successful_resource_update_count == 1 else 'resources'} and {successful_service_update_count} {'service' if successful_service_update_count == 1 else 'services'}[/green]"
            )
    if failed_resource_update_count or failed_service_update_count:
        if failed_service_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'}[/red]"
            )
        elif failed_resource_update_count == 0:
            console.print(
                f"[red]Failed to update {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
        else:
            console.print(
                f"[red]Failed to update {failed_resource_update_count} {'resource' if failed_resource_update_count == 1 else 'resources'} and {failed_service_update_count} {'service' if failed_service_update_count == 1 else 'services'}[/red]"
            )
    if successful_resource_replace_count:
        console.print(
            f"[green]Successfully replaced {successful_resource_replace_count} {'resource' if successful_resource_replace_count == 1 else 'resources'}[/green]"
        )
    if failed_resource_replace_count:
        console.print(
            f"[red]Failed to replace {failed_resource_replace_count} {'resource' if failed_resource_replace_count == 1 else 'resources'}[/red]"
        )
    if successful_service_promote_count:
        console.print(
            f"[green]Successfully promoted {successful_service_promote_count} {'service' if successful_service_promote_count == 1 else 'services'}[/green]"
        )
    if failed_service_promote_count:
        console.print(
            f"[red]Failed to promote {failed_service_promote_count} {'service' if failed_service_promote_count == 1 else 'services'}[/red]"
        )

    console.print()

    return flow_result
