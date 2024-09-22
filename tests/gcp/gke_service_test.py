import os
import unittest
from unittest import mock

import pytest

from launchflow.config import config
from launchflow.gcp.artifact_registry_repository import ArtifactRegistryOutputs
from launchflow.gcp.gke_service import (
    GKECluster,
    GKEService,
    GKEServiceReleaseInputs,
    NodePool,
)
from launchflow.gcp.global_ip_address import GlobalIPAddressOutputs
from launchflow.gcp.ssl import ManagedSSLCertificateOutputs
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import DNSOutputs, DNSRecord, ServiceOutputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class GKEServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.dev_launchflow_uri = LaunchFlowURI(
            project_name="test-project",
            environment_name="dev-test-environment",
        )
        self.prod_launchflow_uri = LaunchFlowURI(
            project_name="test-project",
            environment_name="prod-test-environment",
        )
        self.dev_gcp_environment_config = GCPEnvironmentConfig(
            project_id="test-dev-project",
            default_region="us-central1",
            default_zone="us-central1-a",
            service_account_email="test-dev-service-account",
            artifact_bucket="test-dev-artifacts",
        )
        self.prod_gcp_environment_config = GCPEnvironmentConfig(
            project_id="test-prod-project",
            default_region="us-central1",
            default_zone="us-central1-a",
            service_account_email="test-prod-service-account",
            artifact_bucket="test-prod-artifacts",
        )
        self.cluster = GKECluster("my-cluster")
        self.launchflow_yaml_abspath = os.path.dirname(
            os.path.abspath(config.launchflow_yaml.config_path)
        )

    @mock.patch("launchflow.gcp.gke_service.build_artifact_registry_docker_image")
    async def test_build_gke_service(self, build_docker_mock: mock.MagicMock):
        build_docker_mock.return_value = "fake-docker-image:latest"

        gke_service = GKEService("service_name", cluster=self.cluster)

        # Setup the resource output mocks
        artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="test-docker-repository",
        )
        gke_service._artifact_registry.outputs = mock.MagicMock(
            return_value=artifact_registry_outputs
        )

        # Run the build and validate the result / mock calls
        release_inputs = await gke_service._build(
            gcp_environment_config=self.dev_gcp_environment_config,
            launchflow_uri=self.dev_launchflow_uri,
            deployment_id="test-deployment-id",
            build_log_file=mock.MagicMock(),
            build_local=False,
        )

        self.assertEqual(release_inputs.docker_image, "fake-docker-image:latest")

        build_docker_mock.assert_called_once_with(
            dockerfile_path="Dockerfile",
            build_directory=self.launchflow_yaml_abspath,
            build_ignore=mock.ANY,
            build_log_file=mock.ANY,
            artifact_registry_repository="test-docker-repository",
            launchflow_project_name=self.dev_launchflow_uri.project_name,
            launchflow_environment_name=self.dev_launchflow_uri.environment_name,
            launchflow_service_name="service_name",
            launchflow_deployment_id="test-deployment-id",
            gcp_environment_config=self.dev_gcp_environment_config,
            build_local=False,
        )

    @mock.patch("launchflow.gcp.gke_service.promote_artifact_registry_docker_image")
    async def test_promote_gke_service(self, promote_docker_mock: mock.MagicMock):
        promote_docker_mock.return_value = "fake-docker-image:latest"

        gke_service = GKEService("service_name", cluster=self.cluster)

        # Setup the resource output mocks
        from_artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="from-docker-repository",
        )
        to_artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="to-docker-repository",
        )
        gke_service._artifact_registry.outputs = mock.MagicMock(
            side_effect=[from_artifact_registry_outputs, to_artifact_registry_outputs]
        )

        # Run the promote and validate the result / mock calls
        release_inputs = await gke_service._promote(
            from_gcp_environment_config=self.dev_gcp_environment_config,
            to_gcp_environment_config=self.prod_gcp_environment_config,
            from_launchflow_uri=self.dev_launchflow_uri,
            to_launchflow_uri=self.prod_launchflow_uri,
            from_deployment_id="test-from-deployment-id",
            to_deployment_id="test-to-deployment-id",
            promote_log_file=mock.MagicMock(),
            promote_local=False,
        )

        self.assertEqual(release_inputs.docker_image, "fake-docker-image:latest")

        promote_docker_mock.assert_called_once_with(
            build_log_file=mock.ANY,
            from_artifact_registry_repository="from-docker-repository",
            to_artifact_registry_repository="to-docker-repository",
            launchflow_service_name="service_name",
            from_launchflow_deployment_id="test-from-deployment-id",
            to_launchflow_deployment_id="test-to-deployment-id",
            from_gcp_environment_config=self.dev_gcp_environment_config,
            to_gcp_environment_config=self.prod_gcp_environment_config,
            promote_local=False,
        )

    @mock.patch("launchflow.gcp.gke_service._get_gke_config")
    @mock.patch("launchflow.gcp.gke_service.update_k8s_service")
    @mock.patch("launchflow.gcp.gke_service.k8_config.load_kube_config_from_dict")
    @mock.patch("google.cloud.container_v1.ClusterManagerAsyncClient.get_cluster")
    async def test_release_gke_service_successful(
        self,
        get_cluster_mock: mock.MagicMock,
        load_kube_mock: mock.MagicMock,
        update_k8s_service_mock: mock.MagicMock,
        get_gke_config_mock: mock.MagicMock,
    ):
        gke_service = GKEService("service_name", cluster=self.cluster)

        # Setup the resource output mocks
        get_cluster_mock.return_value = mock.MagicMock()
        update_k8s_service_mock.return_value = mock.MagicMock()
        get_gke_config_mock.return_value = mock.MagicMock()

        await gke_service._release(
            release_inputs=GKEServiceReleaseInputs(
                docker_image="gcr.io/test-project/test-image:foo"
            ),
            gcp_environment_config=self.dev_gcp_environment_config,
            launchflow_uri=self.dev_launchflow_uri,
            deployment_id="test-deployment-id",
            release_log_file=mock.MagicMock(),
        )

        load_kube_mock.assert_called_once_with(mock.ANY)
        update_k8s_service_mock.assert_called_once_with(
            docker_image="gcr.io/test-project/test-image:foo",
            namespace="default",
            service_name="service_name",
            deployment_id="test-deployment-id",
            launchflow_environment=self.dev_launchflow_uri.environment_name,
            launchflow_project=self.dev_launchflow_uri.project_name,
            artifact_bucket="gs://test-dev-artifacts",
            cloud_provider="gcp",
            k8_service_account="test-dev-service-account",
            environment_vars=None,
        )

    # TODO: Add custom domain mapping tests
    async def test_gke_service_outputs(self):
        node_pool = NodePool(
            "my-node-pool", cluster=self.cluster, machine_type="e2-micro"
        )
        gke_service = GKEService(
            "service_name", cluster=self.cluster, node_pool=node_pool
        )
        custom_url_gke_service = GKEService(
            "service_name",
            cluster=self.cluster,
            domain="test.com",
            service_type="NodePort",
        )

        # Setup the resource output mocks
        container_outputs = mock.MagicMock(
            internal_ip="1.2.3.4",
            external_ip="2.3.4.5",
        )
        gke_service.container.outputs = mock.MagicMock(return_value=container_outputs)
        custom_url_gke_service.container.outputs = mock.MagicMock(
            return_value=container_outputs
        )

        ip_address_outputs = GlobalIPAddressOutputs(
            ip_address="1.2.3.4",
        )
        custom_url_gke_service._ip_address.outputs = mock.MagicMock(  # type: ignore
            return_value=ip_address_outputs
        )

        ssl_outputs = ManagedSSLCertificateOutputs(
            domains=["test.com"],
        )
        custom_url_gke_service._ssl_certificate.outputs = mock.MagicMock(  # type: ignore
            return_value=ssl_outputs
        )

        # Fetch the outputs and assert that they are correct
        default_service_outputs = gke_service.outputs()
        self.assertEqual(
            default_service_outputs,
            ServiceOutputs(
                service_url="http://2.3.4.5",
                dns_outputs=None,
            ),
        )

        custom_url_service_outputs = custom_url_gke_service.outputs()
        self.assertEqual(
            custom_url_service_outputs,
            ServiceOutputs(
                service_url="http://2.3.4.5",
                dns_outputs=DNSOutputs(
                    domain="test.com",
                    dns_records=[
                        DNSRecord(
                            dns_record_value="1.2.3.4",
                            dns_record_type="A",
                        ),
                    ],
                ),
            ),
        )
