import unittest
from unittest import mock

import pytest
from google.cloud import compute

from launchflow.gcp.compute_engine_service import ComputeEngineService
from launchflow.gcp.gke import GKECluster
from launchflow.gcp.gke_service import GKEService
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.service import ServiceOutputs
from launchflow.workflows.deploy_gcp_service import (
    release_docker_image_to_compute_engine,
    release_docker_image_to_gke,
)


class FakeExtendedOperation:
    def __init__(self, calls: int = 1):
        self.calls = calls

    def result(self):
        return True

    def done(self):
        self.calls -= 1
        return self.calls <= 0


@pytest.mark.usefixtures("launchflow_yaml_local_backend_fixture")
class DeployGcpServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service_manager = ServiceManager(
            project_name="launchflow-caleb",
            environment_name="staging",
            service_name="service",
            # NOTE: we set this to none since the test doesn't actually use it
            backend=None,  # type: ignore
        )
        self.gcp_environment_config = GCPEnvironmentConfig(
            project_id="launchflow-caleb",
            default_zone="us-central1-a",
            default_region="us-central1",
            service_account_email="sa@sa.com",
            artifact_bucket="launchflow-caleb-artifacts",
        )
        self.docker_image = "gcr.io/launchflow-caleb/caleb:latest"
        self.deployment_id = "deployment_id"

    @mock.patch("google.cloud.compute.InstanceTemplatesClient")
    @mock.patch("google.cloud.compute.RegionInstanceGroupManagersClient")
    async def test_release_docker_image_to_compute_engine_success(
        self, group_manager_mock: mock.MagicMock, template_mock: mock.MagicMock
    ):
        # Setup mocks
        template_mock.return_value.insert.return_value = FakeExtendedOperation()
        group_manager_mock.return_value.patch.return_value = FakeExtendedOperation()

        # Setup inputs
        service = ComputeEngineService(
            name=self.service_manager.service_name, domain="test.com"
        )
        # Execute test
        result = await release_docker_image_to_compute_engine(
            docker_image=self.docker_image,
            service_manager=self.service_manager,
            gcp_environment_config=self.gcp_environment_config,
            compute_engine_service=service,
            deployment_id=self.deployment_id,
        )
        # Verify outputs
        assert result == "https://test.com"
        group_manager_mock.return_value.patch.assert_called_once_with(
            instance_group_manager=self.service_manager.service_name,
            project=self.gcp_environment_config.project_id,
            region=self.gcp_environment_config.default_region,
            instance_group_manager_resource=compute.InstanceGroupManager(
                versions=[
                    compute.InstanceGroupManagerVersion(
                        instance_template=f"projects/launchflow-caleb/global/instanceTemplates/service-{self.deployment_id}",
                        name=f"service-{self.deployment_id}",
                    )
                ],
                update_policy=compute.InstanceGroupManagerUpdatePolicy(
                    type_="PROACTIVE"
                ),
            ),
        )
        template = compute.InstanceTemplate(
            name=f"{self.service_manager.service_name}-{self.deployment_id}",
            properties=compute.InstanceProperties(
                disks=[
                    compute.AttachedDisk(
                        auto_delete=True,
                        boot=True,
                        initialize_params=compute.AttachedDiskInitializeParams(
                            disk_size_gb=10,
                            source_image="https://www.googleapis.com/compute/v1/projects/cos-cloud/global/images/cos-stable-109-17800-147-54",
                        ),
                    )
                ],
                labels={"container-vm": "cos-stable-109-17800-147-54"},
                machine_type="e2-standard-2",
                metadata=compute.Metadata(
                    items=[
                        compute.Items(
                            key="google-logging-enabled",
                            value="true",
                        ),
                        compute.Items(
                            key="google-monitoring-enabled",
                            value="true",
                        ),
                        compute.Items(
                            key="gce-container-declaration",
                            value='{"spec": {"containers": [{"image": "gcr.io/launchflow-caleb/caleb:latest", "env": [{"name": "LAUNCHFLOW_ARTIFACT_BUCKET", "value": "gs://launchflow-caleb-artifacts"}, {"name": "LAUNCHFLOW_PROJECT", "value": "launchflow-caleb"}, {"name": "LAUNCHFLOW_ENVIRONMENT", "value": "staging"}, {"name": "LAUNCHFLOW_CLOUD_PROVIDER", "value": "gcp"}, {"name": "LAUNCHFLOW_DEPLOYMENT_ID", "value": "deployment_id"}]}]}, "volumes": [], "restartPolicy": "Always"}',
                        ),
                    ]
                ),
                network_interfaces=[
                    compute.NetworkInterface(
                        access_configs=[
                            compute.AccessConfig(
                                name="External NAT", type_="ONE_TO_ONE_NAT"
                            )
                        ],
                        network="https://www.googleapis.com/compute/beta/projects/launchflow-caleb/global/networks/default",
                    )
                ],
                service_accounts=[
                    compute.ServiceAccount(
                        email="sa@sa.com",
                        scopes=["https://www.googleapis.com/auth/cloud-platform"],
                    )
                ],
                tags=compute.Tags(items=["service"]),
            ),
        )
        template_mock.return_value.insert.assert_called_once_with(
            project=self.gcp_environment_config.project_id,
            instance_template_resource=template,
        )

    @mock.patch("google.cloud.container_v1.ClusterManagerAsyncClient")
    @mock.patch("launchflow.workflows.deploy_gcp_service.update_k8s_service")
    @mock.patch("google.auth.default")
    async def test_deploy_gke_service(
        self,
        creds_mock: mock.MagicMock,
        update_mock: mock.AsyncMock,
        cluster_manager_mock: mock.AsyncMock,
    ):
        cluster = GKECluster("my-cluster")
        service = GKEService(
            self.service_manager.service_name, cluster, environment_variables={"A": "B"}
        )

        service_outputs = ServiceOutputs(
            service_url="https://service.staging.launchflow-caleb.com",
            dns_outputs=None,
        )
        service.outputs = mock.MagicMock(return_value=service_outputs)

        mock_creds = mock.MagicMock()
        mock_creds.valid = True
        creds_mock.return_value = (mock_creds, "project")
        get_cluster_mock = mock.AsyncMock()
        mock_cluster = mock.MagicMock()
        get_cluster_mock.return_value = mock_cluster
        mock_cluster.endpoint = "https://mock"
        mock_cluster.master_auth = mock.MagicMock()
        mock_cluster.master_auth.cluster_ca_certificate = "cert"
        cluster_manager_mock.return_value.get_cluster = get_cluster_mock
        result = await release_docker_image_to_gke(
            docker_image=self.docker_image,
            service_manager=self.service_manager,
            gcp_environment_config=self.gcp_environment_config,
            gke_service=service,
            deployment_id=self.deployment_id,
        )

        assert result == service_outputs.service_url

        cluster_manager_mock.return_value.get_cluster.assert_called_once_with(
            name="projects/launchflow-caleb/locations/us-central1-a/clusters/my-cluster"
        )
        update_mock.assert_called_once_with(
            docker_image=self.docker_image,
            namespace="default",
            service_name=self.service_manager.service_name,
            deployment_id=self.deployment_id,
            launchflow_environment=self.service_manager.environment_name,
            launchflow_project=self.service_manager.project_name,
            artifact_bucket=f"gs://{self.gcp_environment_config.artifact_bucket}",
            cloud_provider="gcp",
            k8_service_account="sa",
            environment_vars={"A": "B"},
        )
