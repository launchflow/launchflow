import asyncio
import time
from typing import Dict, Optional

from kubernetes import client


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
    environment_vars: Optional[Dict[str, str]],
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

    env_vars = [
        client.V1EnvVar(name="LAUNCHFLOW_ARTIFACT_BUCKET", value=artifact_bucket),
        client.V1EnvVar(name="LAUNCHFLOW_PROJECT", value=launchflow_project),
        client.V1EnvVar(name="LAUNCHFLOW_ENVIRONMENT", value=launchflow_environment),
        client.V1EnvVar(name="LAUNCHFLOW_CLOUD_PROVIDER", value=cloud_provider),
        client.V1EnvVar(name="LAUNCHFLOW_DEPLOYMENT_ID", value=deployment_id),
    ]

    if environment_vars is not None:
        for key, val in environment_vars.items():
            env_vars.append(client.V1EnvVar(name=key, value=val))

    container.env = env_vars

    # Update the deployment
    _ = app_client.patch_namespaced_deployment(
        name=service_name, namespace=namespace, body=deployment
    )

    # Wait for the rollout to complete
    await _wait_for_deployment_rollout(app_client, service_name, namespace)


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
