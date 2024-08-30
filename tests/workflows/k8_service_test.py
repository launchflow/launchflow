import unittest
from unittest import mock

from kubernetes import client

from launchflow.workflows.k8s_service import update_k8s_service


class K8ServiceTest(unittest.IsolatedAsyncioTestCase):
    @mock.patch("launchflow.workflows.k8s_service.client")
    async def test_update_k8s_service(self, k8_client_mock: mock.MagicMock):
        # Setup inputs
        docker_image = "gcr.io/launchflow-test/test:latest"
        service_name = "service"
        namespace = "namespace"
        artifact_bucket = "gs://launchflow-test-artifacts"
        launchflow_project = "launchflow-test"
        launchflow_environment = "staging"
        k8_service_account = "service-account"
        cloud_provider = "gcp"
        deployment_id = "deployment_id"
        environment_vars = {"A": "B"}

        # Setup mocks
        k8_client_mock.V1EnvVar = client.V1EnvVar
        apps_client = mock.MagicMock()
        k8_client_mock.AppsV1Api.return_value = apps_client

        mock_deployment = mock.MagicMock()
        apps_client.read_namespaced_deployment.return_value = mock_deployment

        mock_deployment_status = mock.MagicMock()
        mock_deployment_status.status.updated_replicas = 1
        mock_deployment_status.status.replicas = 1
        mock_deployment_status.status.available_replicas = 1
        mock_deployment_status.spec.replicas = 1
        apps_client.read_namespaced_deployment_status.return_value = (
            mock_deployment_status
        )

        _ = await update_k8s_service(
            docker_image=docker_image,
            service_name=service_name,
            namespace=namespace,
            artifact_bucket=artifact_bucket,
            launchflow_project=launchflow_project,
            launchflow_environment=launchflow_environment,
            k8_service_account=k8_service_account,
            cloud_provider=cloud_provider,
            deployment_id=deployment_id,
            environment_vars=environment_vars,
        )

        apps_client.read_namespaced_deployment.assert_called_once_with(
            name=service_name, namespace=namespace
        )
        apps_client.patch_namespaced_deployment.assert_called_once_with(
            name=service_name, namespace=namespace, body=mock_deployment
        )
        apps_client.read_namespaced_deployment_status.assert_called_once_with(
            name=service_name, namespace=namespace
        )
        # Verify that the container spec was updated appropriately
        self.assertEqual(
            mock_deployment.spec.template.spec.containers[0].image, docker_image
        )
        self.assertEqual(
            mock_deployment.spec.template.spec.containers[0].env,
            [
                client.V1EnvVar(
                    name="LAUNCHFLOW_ARTIFACT_BUCKET",
                    value=artifact_bucket,
                ),
                client.V1EnvVar(name="LAUNCHFLOW_PROJECT", value=launchflow_project),
                client.V1EnvVar(
                    name="LAUNCHFLOW_ENVIRONMENT", value=launchflow_environment
                ),
                client.V1EnvVar(name="LAUNCHFLOW_CLOUD_PROVIDER", value=cloud_provider),
                client.V1EnvVar(name="LAUNCHFLOW_DEPLOYMENT_ID", value=deployment_id),
                client.V1EnvVar(name="A", value="B"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
