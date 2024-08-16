import os
import random
import subprocess
import unittest

import pytest


@pytest.mark.integration
class ProjectsIntegrationTest(unittest.TestCase):
    def test_project_flows(self):
        working_dir = os.path.dirname(os.path.realpath(__file__))
        random_int = random.randint(1, 1000)
        project_a = f"integration-test-project-{random_int}"
        project_b = f"integration-test-project-{random_int + 1}"

        # Step 1: Create the projects
        for project in [project_a, project_b]:
            subprocess.check_call(
                f"lf projects create -y {project}",
                shell=True,
                cwd=working_dir,
            )

        # Step 2: List the projects
        projects = subprocess.check_output(
            "lf projects list", shell=True, cwd=working_dir
        ).decode("utf-8")
        self.assertIn(project_a, projects)

        # Step 3: Delete the first project
        subprocess.check_call(
            f"lf projects delete -y {project_a}",
            shell=True,
            cwd=working_dir,
        )

        # Step 4: List the projects
        projects = subprocess.check_output(
            "lf projects list", shell=True, cwd=working_dir
        ).decode("utf-8")
        self.assertNotIn(project_a, projects)
        self.assertIn(project_b, projects)

        # Step 5: Delete the second project
        subprocess.check_call(
            f"lf projects delete -y {project_b}",
            shell=True,
            cwd=working_dir,
        )


if __name__ == "__main__":
    unittest.main()
