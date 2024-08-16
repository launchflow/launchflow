import os
import random
import signal
import subprocess
import time
import unittest

import httpx
import pytest


@pytest.mark.integration
class AWSIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Create environment
        cls.working_dir = os.path.dirname(os.path.realpath(__file__))
        cls.environment_name = f"aws-dev-{random.randint(1, 1000)}"
        subprocess.check_call(
            f"lf environments create -y --cloud-provider=aws --env-type=development {cls.environment_name}",
            shell=True,
            cwd=cls.working_dir,
        )
        # Create resources
        subprocess.check_call(
            f"lf create -y {cls.environment_name}", shell=True, cwd=cls.working_dir
        )

    @classmethod
    def tearDownClass(cls) -> None:
        # Destroy resource
        subprocess.check_call(
            f"lf destroy -y {cls.environment_name}", shell=True, cwd=cls.working_dir
        )
        # Destroy environment
        subprocess.check_call(
            f"lf environments delete {cls.environment_name} -y",
            shell=True,
            cwd=cls.working_dir,
        )

    def test_aws_local(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        url = "http://localhost:8787"
        # 1. Create resources
        process = subprocess.Popen(
            f"lf run {self.environment_name} -- uvicorn main:app --port 8787",
            shell=True,
            cwd=dir_path,
        )
        try:
            # Wait for the process to start
            time.sleep(5)
            with httpx.Client() as client:
                response = client.get(f"{url}/bucket")
                self.assertEqual(response.status_code, 200)
                response = client.get(f"{url}/db")
                self.assertEqual(response.status_code, 200)
                response = client.get(f"{url}/secret")
                self.assertEqual(response.status_code, 200)
                response = client.get(f"{url}/ec2_pg")
                self.assertEqual(response.status_code, 200)
                response = client.get(f"{url}/ec2_redis")
                self.assertEqual(response.status_code, 200)
        finally:
            process.send_signal(signal.SIGINT)
            process.wait()


if __name__ == "__main__":
    unittest.main()
