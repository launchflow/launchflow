import asyncio
import datetime
from contextlib import contextmanager

import launchflow
from launchflow import exceptions
from launchflow.docker.resource import DockerResource
from launchflow.managers.docker_resource_manager import DockerResourceManager
from launchflow.models.enums import ResourceStatus
from launchflow.models.flow_state import ResourceState
from launchflow.workflows.manage_docker.manage_docker_resources import (
    create_docker_resource,
    destroy_docker_resource,
    replace_docker_resource,
)
from launchflow.workflows.manage_docker.schemas import (
    CreateResourceDockerInputs,
    DestroyResourceDockerInputs,
)


async def _create_test_resource(resource: DockerResource):
    manager = DockerResourceManager(
        project_name=launchflow.project,
        environment_name=launchflow.environment,
        resource_name=resource.name,
    )
    new_inputs = resource.inputs().to_dict()
    try:
        resource_state = await manager.load_resource()
        new_inputs
        if resource_state.inputs == new_inputs:
            op_type = "noop"
        else:
            op_type = "replace"
        resource_state.inputs = new_inputs
        resource_state.created_at = datetime.datetime.now()
        resource_state.updated_at = datetime.datetime.now()
        resource_state.status = ResourceStatus.UPDATING
    except exceptions.ResourceNotFound:
        op_type = "create"
        resource_state = ResourceState(
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
            name=resource.name,
            cloud_provider=None,
            product=resource.product,
            inputs=new_inputs,
            status=ResourceStatus.CREATING,
        )
    inputs = CreateResourceDockerInputs(
        resource=resource_state,
        image=resource.docker_image,
        env_vars=resource.env_vars,
        command=resource.command,  # type: ignore
        ports=resource.ports,
        environment_name=launchflow.environment,
        resource_inputs=new_inputs,
        logs_file=None,
    )
    if op_type == "noop":
        print(f"Resource `{resource.name}` is up to date.")
        return
    elif op_type == "create":
        print(f"Creating `{resource.name}`...")
        outputs = await create_docker_resource(inputs)
        print("Done creating.")
    elif op_type == "replace":
        print(f"Replacing `{resource.name}`...")
        outputs = await replace_docker_resource(inputs)
        print("Done updating.")
    resource_state.status = ResourceStatus.READY
    resource.ports.update(outputs.ports)
    resource.running_container_id = outputs.container.id
    await manager.save_resource(resource_state, "testing")


async def create_test_resources(*resources: DockerResource):
    launchflow.project = "test"
    launchflow.environment = "test"
    coros = []
    for resource in resources:
        coros.append(_create_test_resource(resource))
    await asyncio.gather(*coros)


async def _destroy_test_resource(resource: DockerResource):
    manager = DockerResourceManager(
        project_name=launchflow.project,
        environment_name=launchflow.environment,
        resource_name=resource.name,
    )
    container_id = manager.get_running_container_id()
    if container_id is not None:
        inputs = DestroyResourceDockerInputs(
            container_id=container_id,
            logs_file=None,
        )
        print(f"Destroying `{resource.name}...`")
        await destroy_docker_resource(inputs)
        print("Done destroying.")


async def destroy_test_resources(*resources: DockerResource):
    launchflow.project = "test"
    launchflow.environment = "test"
    coros = []
    for resource in resources:
        coros.append(_destroy_test_resource(resource))
    await asyncio.gather(*coros)


@contextmanager
def test_resources(*resources: DockerResource):
    try:
        asyncio.run(create_test_resources(*resources))
        yield
    finally:
        asyncio.run(destroy_test_resources(*resources))
