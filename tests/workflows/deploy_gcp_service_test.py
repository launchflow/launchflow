import unittest
from unittest import mock

from google.cloud import compute

from launchflow.gcp.compute_engine_service import ComputeEngineService
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.workflows.deploy_gcp_service import (
    release_docker_image_to_compute_engine,
)


class FakeExtendedOperation:
    def __init__(self, calls: int = 1):
        self.calls = calls

    def result(self):
        return True

    def done(self):
        self.calls -= 1
        return self.calls <= 0


class DeployGcpServiceTest(unittest.IsolatedAsyncioTestCase):
    @mock.patch("google.cloud.compute.InstanceTemplatesClient")
    @mock.patch("google.cloud.compute.RegionInstanceGroupManagersClient")
    async def test_release_docker_image_to_compute_engine_success(
        self, group_manager_mock: mock.MagicMock, template_mock: mock.MagicMock
    ):
        # Setup mocks
        template_mock.return_value.insert.return_value = FakeExtendedOperation()
        group_manager_mock.return_value.patch.return_value = FakeExtendedOperation()

        # Setup inputs
        docker_image = "gcr.io/launchflow-caleb/caleb:latest"
        service_manager = ServiceManager(
            project_name="launchflow-caleb",
            environment_name="staging",
            service_name="service",
            # NOTE: we set this to none since the test doesn't actually use it
            backend=None,  # type: ignore
        )
        gcp_environment_config = GCPEnvironmentConfig(
            project_id="launchflow-caleb",
            default_zone="us-central1-a",
            default_region="us-central1",
            service_account_email="sa@sa.com",
            artifact_bucket="launchflow-caleb-artifacts",
        )
        service = ComputeEngineService(name="service", domain="test.com")
        deployment_id = "deployment_id"
        # Execute test
        result = await release_docker_image_to_compute_engine(
            docker_image=docker_image,
            service_manager=service_manager,
            gcp_environment_config=gcp_environment_config,
            compute_engine_service=service,
            deployment_id=deployment_id,
        )
        # Verify outputs
        assert result == "https://test.com"
        group_manager_mock.return_value.patch.assert_called_once_with(
            instance_group_manager="service",
            project="launchflow-caleb",
            region="us-central1",
            instance_group_manager_resource=compute.InstanceGroupManager(
                versions=[
                    compute.InstanceGroupManagerVersion(
                        instance_template=f"projects/launchflow-caleb/global/instanceTemplates/service-{deployment_id}",
                        name=f"service-{deployment_id}",
                    )
                ],
                update_policy=compute.InstanceGroupManagerUpdatePolicy(
                    type_="PROACTIVE"
                ),
            ),
        )
        template = compute.InstanceTemplate(
            name="service-deployment_id",
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
            project=gcp_environment_config.project_id,
            instance_template_resource=template,
        )
