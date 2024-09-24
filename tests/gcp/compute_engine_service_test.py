import os
import unittest
from datetime import timedelta
from unittest import mock

import pytest

from launchflow.config import config
from launchflow.gcp.artifact_registry_repository import ArtifactRegistryOutputs
from launchflow.gcp.compute_engine_service import (
    ComputeEngineService,
    ComputeEngineServiceReleaseInputs,
)
from launchflow.gcp.global_ip_address import GlobalIPAddressOutputs
from launchflow.gcp.ssl import ManagedSSLCertificateOutputs
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.service import DNSOutputs, DNSRecord, ServiceOutputs


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class ComputeEngineServiceTest(unittest.IsolatedAsyncioTestCase):
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
        self.launchflow_yaml_abspath = os.path.dirname(
            os.path.abspath(config.launchflow_yaml.config_path)
        )

    @mock.patch(
        "launchflow.gcp.compute_engine_service.build_artifact_registry_docker_image"
    )
    async def test_build_compute_engine_service(
        self, build_docker_mock: mock.MagicMock
    ):
        build_docker_mock.return_value = "fake-docker-image:latest"

        compute_engine_service = ComputeEngineService("service_name")

        # Setup the resource output mocks
        artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="test-docker-repository",
        )
        compute_engine_service._artifact_registry.outputs = mock.MagicMock(
            return_value=artifact_registry_outputs
        )

        # Run the build and validate the result / mock calls
        release_inputs = await compute_engine_service._build(
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

    @mock.patch(
        "launchflow.gcp.compute_engine_service.promote_artifact_registry_docker_image"
    )
    async def test_promote_compute_engine_service(
        self, promote_docker_mock: mock.MagicMock
    ):
        promote_docker_mock.return_value = "fake-docker-image:latest"

        compute_engine_service = ComputeEngineService("service_name")

        # Setup the resource output mocks
        from_artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="from-docker-repository",
        )
        to_artifact_registry_outputs = ArtifactRegistryOutputs(
            docker_repository="to-docker-repository",
        )
        compute_engine_service._artifact_registry.outputs = mock.MagicMock(
            side_effect=[from_artifact_registry_outputs, to_artifact_registry_outputs]
        )

        # Run the promote and validate the result / mock calls
        release_inputs = await compute_engine_service._promote(
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

    # TODO: Think of a better way to test the release, this is pretty much 100% mocked
    # and doesn't really test the actual release process
    @mock.patch("launchflow.gcp.compute_engine_service._release_compute_engine_service")
    async def test_release_compute_engine_service_successful(
        self, release_compute_engine_service_mock: mock.MagicMock
    ):
        compute_engine_service = ComputeEngineService(
            "service_name",
            machine_type="e2-medium",
            disk_size_gb=10,
            region="us-central1",
            deploy_timeout=timedelta(minutes=10),
        )

        compute_engine_service._mig.resource_id = "test-mig-id"

        # Run the release and validate the result
        await compute_engine_service._release(
            release_inputs=ComputeEngineServiceReleaseInputs(
                docker_image="gcr.io/test-project/test-image:foo"
            ),
            gcp_environment_config=self.dev_gcp_environment_config,
            launchflow_uri=self.dev_launchflow_uri,
            deployment_id="test-deployment-id",
            release_log_file=mock.MagicMock(),
        )

        release_compute_engine_service_mock.assert_called_once_with(
            docker_image="gcr.io/test-project/test-image:foo",
            machine_type="e2-medium",
            disk_size_gb=10,
            deploy_timeout=timedelta(minutes=10),
            gcp_environment_config=self.dev_gcp_environment_config,
            launchflow_uri=self.dev_launchflow_uri,
            deployment_id="test-deployment-id",
            service_name="service_name",
            mig_resource_id="test-mig-id",
            region="us-central1",
        )

    # TODO: Add custom domain mapping tests
    async def test_compute_engine_service_outputs(self):
        default_compute_engine_service = ComputeEngineService("service_name")
        custom_url_compute_engine_service = ComputeEngineService(
            "service_name", domain="test.com"
        )

        # Setup the resource output mocks
        ip_address_outputs = GlobalIPAddressOutputs(
            ip_address="1.2.3.4",
        )
        custom_url_compute_engine_service._ip_address.outputs = mock.MagicMock(  # type: ignore
            return_value=ip_address_outputs
        )

        ssl_outputs = ManagedSSLCertificateOutputs(
            domains=["test.com"],
        )
        custom_url_compute_engine_service._ssl_certificate.outputs = mock.MagicMock(  # type: ignore
            return_value=ssl_outputs
        )

        # Fetch the outputs and assert that they are correct
        default_service_outputs = default_compute_engine_service.outputs()
        self.assertEqual(
            default_service_outputs,
            ServiceOutputs(
                service_url="Unsuppported - custom domain required",
                dns_outputs=None,
            ),
        )

        custom_url_service_outputs = custom_url_compute_engine_service.outputs()
        self.assertEqual(
            custom_url_service_outputs,
            ServiceOutputs(
                service_url="https://test.com",
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
