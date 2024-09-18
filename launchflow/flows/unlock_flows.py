from launchflow.locks import LockOperation, OperationType
from launchflow.managers.resource_manager import ResourceManager
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.enums import ResourceStatus, ServiceStatus


async def unlock_resource(resource_manager: ResourceManager):
    # First force unlock the resource
    resource = await resource_manager.load_resource()
    try:
        await resource_manager.force_unlock_resource()
    except Exception as e:
        if not resource.status.is_pending():
            raise e

    # Next lock the resource and update the status
    async with await resource_manager.lock_resource(
        LockOperation(operation_type=OperationType.UPDATE_RESOURCE)
    ) as lock:
        resource = await resource_manager.load_resource()
        if resource.status == ResourceStatus.CREATING:
            resource.status = ResourceStatus.CREATE_FAILED
        elif resource.status == ResourceStatus.DESTROYING:
            resource.status = ResourceStatus.DELETE_FAILED
        elif resource.status == ResourceStatus.UPDATING:
            resource.status = ResourceStatus.UPDATE_FAILED
        elif resource.status == ResourceStatus.REPLACING:
            resource.status = ResourceStatus.REPLACE_FAILED

        await resource_manager.save_resource(resource, lock.lock_id)


async def unlock_service(service_manager: ServiceManager):
    # First force unlock the service
    service = await service_manager.load_service()
    try:
        await service_manager.force_unlock_service()
    except Exception as e:
        if not service.status.is_pending():
            raise e

    # Next lock the service and update the status
    async with await service_manager.lock_service(
        LockOperation(operation_type=OperationType.UPDATE_SERVICE)
    ) as lock:
        service = await service_manager.load_service()
        if service.status == ServiceStatus.CREATING:
            service.status = ServiceStatus.CREATE_FAILED
        elif service.status == ServiceStatus.DESTROYING:
            service.status = ServiceStatus.DESTROYING
        elif service.status == ServiceStatus.UPDATING:
            service.status = ServiceStatus.UPDATE_FAILED
        elif service.status == ServiceStatus.DEPLOYING:
            service.status = ServiceStatus.DEPLOY_FAILED
        await service_manager.save_service(service, lock.lock_id)
