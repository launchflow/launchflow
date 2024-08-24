import logging
import os
import tempfile

from launchflow.cli.ast_search import (
    find_launchflow_deployments,
    find_launchflow_resources,
)

SERVICE_PY = """\
import launchflow as lf

service = lf.gcp.CloudRun("name")
"""

TEST_DIR = os.path.join(os.path.dirname(__file__), "test_apps")


def test_find_launchflow_resources(caplog):
    with caplog.at_level(logging.ERROR):
        resources = find_launchflow_resources(TEST_DIR, ignore_roots=["should_ignore"])

    resources.sort()
    assert resources == [
        "alias_import:bucket",
        "basic:bucket",
        "full_path_import:bucket",
        "full_path_import:custom_bucket",
        "inner_resource:bucket",
    ]

    assert (
        "launchflow.gcp.GCSBucket(inner-bucket) is not defined as a global variable and will be ignored"
        in caplog.text
    )
    assert (
        "launchflow.gcp.GCSBucket(inner-class-bucket) is not defined as a global variable and will be ignored"
        in caplog.text
    )


def test_find_launchflow_services(caplog):
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(os.path.join(temp_dir, "service.py"), "w") as f:
            f.write(SERVICE_PY)
        with caplog.at_level(logging.ERROR):
            services = find_launchflow_deployments(
                temp_dir, ignore_roots=["should_ignore"]
            )

    services.sort()
    assert services == ["service:service"]


def test_ignored_services_and_resources(caplog):
    with caplog.at_level(logging.ERROR):
        resources = find_launchflow_resources(TEST_DIR, ignore_roots=[])
        services = find_launchflow_deployments(TEST_DIR, ignore_roots=[])

    resources.sort()
    assert resources == [
        "alias_import:bucket",
        "basic:bucket",
        "full_path_import:bucket",
        "full_path_import:custom_bucket",
        "inner_resource:bucket",
        # Ignored resources should be included since ignore_roots is empty
        "should_ignore.basic:bucket",
    ]
    assert services == [
        "should_ignore.basic:service",
    ]

    with caplog.at_level(logging.ERROR):
        resources = find_launchflow_resources(TEST_DIR, ignore_roots=["should_ignore"])
        services = find_launchflow_deployments(TEST_DIR, ignore_roots=["should_ignore"])

    resources.sort()
    # Ignored resources should not be included since ignore_roots is not empty
    assert resources == [
        "alias_import:bucket",
        "basic:bucket",
        "full_path_import:bucket",
        "full_path_import:custom_bucket",
        "inner_resource:bucket",
    ]
    assert services == []
