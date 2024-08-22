import os
import random
import time
import subprocess
import unittest
from typing import List

import boto3
import pytest
import yaml
from botocore.exceptions import ClientError
from google.api_core.exceptions import NotFound
from google.cloud import resourcemanager_v3, storage


def is_vpc_deleted(vpc_id: str) -> bool:
    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_vpcs(VpcIds=[vpc_id])

        if not response["Vpcs"]:
            return True
        return False
    except ClientError as error:
        if error.response["Error"]["Code"] == "InvalidVpcID.NotFound":
            return True
        else:
            raise


def is_gcp_project_deleted(project_id: str) -> bool:
    client = resourcemanager_v3.ProjectsClient()
    project_name = f"projects/{project_id}"

    try:
        project = client.get_project(name=project_name)
        if project.state == resourcemanager_v3.Project.State.DELETE_REQUESTED:
            return True
        return False
    except NotFound:
        return True


def list_gcp_buckets(project_id: str) -> List[str]:
    try:
        client = storage.Client(project=project_id)
        buckets = client.list_buckets()
        return [bucket.name for bucket in buckets]
    except NotFound:
        return []


def delete_gcp_project(project_id: str) -> None:
    client = resourcemanager_v3.ProjectsClient()
    project_name = f"projects/{project_id}"

    try:
        client.delete_project(name=project_name)
    except NotFound:
        pass


@pytest.mark.integration
class EnvironmentsIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        test_mode = os.environ.get("TEST_MODE")
        if test_mode is None:
            raise ValueError("TEST_MODE environment variable must be set.")

        base_dir = None
        if test_mode == "local":
            base_dir = "local-backend"
        elif test_mode == "lf-cloud":
            base_dir = "lf-cloud-backend"
        elif test_mode == "gcs":
            base_dir = "gcs-backend"
        else:
            raise ValueError(f"Invalid TEST_MODE: {test_mode}")
        cls.working_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), base_dir
        )

    @classmethod
    def tearDownClass(cls) -> None:
        print("=" * 80 + "\n")
        print(
            "⚠️  WARNING: IF THE INTEGRATION TEST FAILED NOT ALL RESOURCE WILL BE CLEANED UP."
        )
        print(
            "⚠️  WARNING: Please run: \n\t - `lf destroy` for every environment\n\t`lf environments delete` for all environments."
        )
        print("\n" + "=" * 80)

    def run_commands(self, cmds: List[str]):
        procs = []
        for cmd in cmds:
            procs.append(subprocess.Popen(cmd, shell=True, cwd=self.working_dir))
        for proc in procs:
            return_code = proc.wait()
            self.assertEqual(return_code, 0, f"Command failed: {proc.args}")

    def test_gcp_environment_flows(self):
        random_int = random.randint(1, 1000)
        environment_a = f"test-env-{random_int}"
        environment_b = f"test-env-{random_int + 1}"
        environments = [environment_a, environment_b]

        # Step 1: Create the GCP environments
        env_create_cmds = []
        for env in environments:
            env_create_cmds.append(
                f"lf --log-level=DEBUG environments create {env} --env-type=development --cloud-provider=gcp -y"
            )
        self.run_commands(env_create_cmds)

        # Step 2: List the environments
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list --format=yaml",
            shell=True,
            cwd=self.working_dir,
        ).decode("utf-8")
        self.assertIn(environment_a, list_output)
        self.assertIn(environment_b, list_output)

        # Parse the list output to get the project IDs (for later)
        environments_data = yaml.safe_load(list_output)

        # Step 3a: Add a resource to both environments
        create_cmds = []
        for env in environments:
            create_cmds.append(f"lf --log-level=DEBUG create {env} -y")
        self.run_commands(create_cmds)

        # Add a sleep to allow iam permissions to propagate
        print("Waiting 60 seconds for IAM permissions to propagate...")
        time.sleep(60)

        # Step 3b: Add a service to both environments
        deploy_cmds = []
        for env in environments:
            deploy_cmds.append(f"lf --log-level=DEBUG deploy {env} -y")
        self.run_commands(deploy_cmds)

        # Step 4: Try to delete the first environment (should fail with Not Empty)
        with self.assertRaises(subprocess.CalledProcessError) as context:
            subprocess.run(
                f"lf --log-level=DEBUG environments delete {environment_a} -y",
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        output = context.exception.stdout
        self.assertIn(f"Environment '{environment_a}' is not empty.", output)

        # Step 5: Delete the resources and services from the first environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG destroy {environment_a} -y",
            shell=True,
            cwd=self.working_dir,
        )

        # Step 6: Delete the first environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG environments delete {environment_a} -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 7: List the environments
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list", shell=True, cwd=self.working_dir
        ).decode("utf-8")
        self.assertNotIn(environment_a, list_output)
        self.assertIn(environment_b, list_output)

        # Step 8: Delete just the services from the second environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG destroy {environment_b} --service fastapi-service -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 9: Try to delete the second environment (should fail with Not Empty)
        with self.assertRaises(subprocess.CalledProcessError) as context:
            subprocess.run(
                f"lf --log-level=DEBUG environments delete {environment_b} -y",
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        output = context.exception.stdout
        self.assertIn(f"Environment '{environment_b}' is not empty.", output)

        # Step 11: Delete the second environment with --detach flag (should be allowed and resources kept around)
        result = subprocess.check_call(
            f"lf environments delete {environment_b} --detach -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 12: List the environments and make sure empty
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list", shell=True, cwd=self.working_dir
        ).decode("utf-8")
        self.assertNotIn(environment_a, list_output)
        self.assertNotIn(environment_b, list_output)

        # Step 13: Use the gcp resource api to make sure the project for environment a is deleted
        project_a_id = environments_data[environment_a]["environment"]["gcp_config"][
            "project_id"
        ]
        self.assertTrue(is_gcp_project_deleted(project_id=project_a_id))

        # Step 14: Use the gcp resource api to make sure the project for environment b is NOT deleted and resources still exist
        project_b_id = environments_data[environment_b]["environment"]["gcp_config"][
            "project_id"
        ]
        self.assertFalse(is_gcp_project_deleted(project_id=project_b_id))
        self.assertIn(
            f"launchflow-integration-tests-{environment_b}-gcs-bucket",
            list_gcp_buckets(project_id=project_b_id),
        )

        # Step 15: Cleanup the project for environment b
        delete_gcp_project(project_id=project_b_id)
        self.assertTrue(is_gcp_project_deleted(project_id=project_b_id))

    def test_aws_environment_flows(self):
        random_int = random.randint(1, 1000)
        environment_a = f"test-env-{random_int}"
        environment_b = f"test-env-{random_int + 1}"
        environments = [environment_a, environment_b]

        # Step 1: Create the GCP environments
        env_cmds = [
            f"lf environments create {env} --env-type=development --cloud-provider=aws -y"
            for env in environments
        ]
        self.run_commands(env_cmds)

        # Step 2: List the environments
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list --format=yaml",
            shell=True,
            cwd=self.working_dir,
        ).decode("utf-8")
        self.assertIn(environment_a, list_output)
        self.assertIn(environment_b, list_output)

        # Parse the list output to get the project IDs (for later)
        environments_data = yaml.safe_load(list_output)

        # Step 3a: Add a resource to both environments
        create_cmds = [f"lf --log-level=DEBUG create {env} -y" for env in environments]
        self.run_commands(create_cmds)

        # Step 3b: Add a service to both environments
        deploy_cmds = [f"lf --log-level=DEBUG deploy {env} -y" for env in environments]
        self.run_commands(deploy_cmds)

        # Step 4: Try to delete the first environment (should fail with Not Empty)
        with self.assertRaises(subprocess.CalledProcessError) as context:
            subprocess.run(
                f"lf --log-level=DEBUG environments delete {environment_a} -y",
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        output = context.exception.stdout
        self.assertIn(f"Environment '{environment_a}' is not empty.", output)

        # Step 5: Delete the resources and services from the first environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG destroy {environment_a} -y",
            shell=True,
            cwd=self.working_dir,
        )

        # Step 6: Delete the first environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG environments delete {environment_a} -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 7: List the environments
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list", shell=True, cwd=self.working_dir
        ).decode("utf-8")
        self.assertNotIn(environment_a, list_output)
        self.assertIn(environment_b, list_output)

        # Step 8: Delete just the services from the second environment
        result = subprocess.check_call(
            f"lf --log-level=DEBUG destroy {environment_b} --service fastapi-service -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 9: Try to delete the second environment (should fail with Not Empty)
        with self.assertRaises(subprocess.CalledProcessError) as context:
            subprocess.run(
                f"lf --log-level=DEBUG environments delete {environment_b} -y",
                shell=True,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                check=True,
            )
        output = context.exception.stdout
        self.assertIn(f"Environment '{environment_b}' is not empty.", output)

        # Step 10: Clean up the rest of the resources so we can delete the environment
        subprocess.check_call(
            f"lf --log-level=DEBUG destroy {environment_b} -y",
            shell=True,
            cwd=self.working_dir,
        )

        # Step 11: Delete the second environment flag
        result = subprocess.check_call(
            f"lf --log-level=DEBUG environments delete {environment_b} -y",
            shell=True,
            cwd=self.working_dir,
        )
        self.assertEqual(result, 0)

        # Step 12: List the environments and make sure empty
        list_output = subprocess.check_output(
            "lf --log-level=DEBUG environments list", shell=True, cwd=self.working_dir
        ).decode("utf-8")
        self.assertNotIn(environment_a, list_output)
        self.assertNotIn(environment_b, list_output)

        # Step 13: Use the aws resource api to make sure the vpc for both environments are deleted
        account_a_vpc_id = environments_data[environment_a]["environment"][
            "aws_config"
        ]["vpc_id"]
        account_b_vpc_id = environments_data[environment_b]["environment"][
            "aws_config"
        ]["vpc_id"]
        self.assertTrue(is_vpc_deleted(vpc_id=account_a_vpc_id))
        self.assertTrue(is_vpc_deleted(vpc_id=account_b_vpc_id))


if __name__ == "__main__":
    unittest.main()
