from kubernetes import client
import asyncio
import time


async def _wait_for_ingress_ip(
    core_client: client.CoreV1Api,
    service_name: str,
    namespace: str,
    timeout: int = 300,
) -> str:
    start_time = time.time()
    while True:
        service = core_client.read_namespaced_service(
            name=service_name, namespace=namespace
        )
        if service.status.load_balancer.ingress:
            return service.status.load_balancer.ingress[0].ip

        if time.time() - start_time > timeout:
            raise TimeoutError(
                f"Timeout waiting for Ingress {service_name} to get an IP address"
            )

        await asyncio.sleep(5)


# TODO: make this async
async def deploy_new_k8s_service(
    k8_client: client.AppsV1Api,
    node_pool_id: str,
    docker_image: str,
    service_name: str,
    port: int,
    namespace: str,
):
    container = client.V1Container(
        name=service_name,
        image=docker_image,
        ports=[client.V1ContainerPort(container_port=port)],
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": service_name}),
        spec=client.V1PodSpec(
            containers=[container],
            node_selector={"nodepool": node_pool_id},
        ),
    )
    spec = client.V1DeploymentSpec(
        replicas=1,
        template=template,
        selector={"matchLabels": {"app": service_name}},
    )
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=spec,
    )
    k8_client.create_namespaced_deployment(namespace=namespace, body=deployment)

    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=service_name),
        spec=client.V1ServiceSpec(
            selector={"app": service_name},
            # TODO: should add options to expose this differently
            ports=[client.V1ServicePort(protocol="TCP", port=port, target_port=port)],
            type="LoadBalancer",
        ),
    )

    core_client = client.CoreV1Api()
    service: client.V1Service = core_client.create_namespaced_service(
        namespace=namespace, body=service
    )  # type: ignore

    ip = await _wait_for_ingress_ip(core_client, service_name, namespace)

    return f"http://{ip}"


async def update_k8s_service(
    docker_image: str,
    service_name: str,
    namespace: str,
    artifact_bucket: str,
    launchflow_project: str,
    launchflow_environment: str,
    k8_service_account: str,
    cloud_provider: str,
    deployment_id: str,
):
    app_client = client.AppsV1Api()
    # Get the current deployment
    deployment: client.V1Deployment = app_client.read_namespaced_deployment(
        name=service_name, namespace=namespace
    )

    # Update the container image
    if deployment.spec is None:
        raise ValueError("Deployment spec is None")
    template_spec = deployment.spec.template.spec
    container = template_spec.containers[0]
    container.image = docker_image
    template_spec.service_account_name = k8_service_account

    container.env = [
        client.V1EnvVar(
            name="LAUNCHFLOW_ARTIFACT_BUCKET", value=f"gs://{artifact_bucket}"
        ),
        client.V1EnvVar(name="LAUNCHFLOW_PROJECT", value=launchflow_project),
        client.V1EnvVar(name="LAUNCHFLOW_ENVIRONMENT", value=launchflow_environment),
        client.V1EnvVar(name="LAUNCHFLOW_CLOUD_PROVIDER", value=cloud_provider),
        client.V1EnvVar(name="LAUNCHFLOW_DEPLOYMENT_ID", value=deployment_id),
    ]

    # Update the deployment
    revision = app_client.patch_namespaced_deployment(
        name=service_name, namespace=namespace, body=deployment
    )

    print("DO NOT SUBMIT: ", revision)

    # Wait for the rollout to complete
    await _wait_for_deployment_rollout(app_client, service_name, namespace)

    core_client = client.CoreV1Api()

    ip = await _wait_for_ingress_ip(core_client, service_name, namespace)
    return f"http://{ip}"


async def _wait_for_deployment_rollout(
    k8_client: client.AppsV1Api,
    deployment_name: str,
    namespace: str,
    timeout: int = 300,
):
    start_time = time.time()
    while True:
        deployment = k8_client.read_namespaced_deployment_status(
            name=deployment_name, namespace=namespace
        )
        print("DO NOT SUBMIT: ", deployment)
        if (
            deployment.status.updated_replicas == deployment.spec.replicas
            and deployment.status.replicas == deployment.spec.replicas
            and deployment.status.available_replicas == deployment.spec.replicas
        ):
            return

        if time.time() - start_time > timeout:
            raise TimeoutError(
                f"Timeout waiting for deployment {deployment_name} to complete rollout"
            )

        await asyncio.sleep(5)
