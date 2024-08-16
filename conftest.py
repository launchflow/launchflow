import pytest

from launchflow.testing.mock_launchflow_yaml import (
    mock_launchflow_yaml_local_backend,
    mock_launchflow_yaml_remote_backend,
)


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        dest="integration",
        default=False,
        help="enable integration tests (marked with integration)",
    )


def pytest_configure(config):
    if not config.option.integration:
        setattr(config.option, "markexpr", "not integration")
    else:
        setattr(config.option, "capture", "no")
        setattr(config.option, "markexpr", "integration")


@pytest.fixture(scope="function")
def launchflow_yaml_local_backend_fixture(request):
    launchflow_yaml_mock = mock_launchflow_yaml_local_backend()
    launchflow_yaml_mock.start()
    request.cls.launchflow_yaml = launchflow_yaml_mock.launchflow_yaml
    yield launchflow_yaml_mock
    launchflow_yaml_mock.stop()


@pytest.fixture(scope="function")
def launchflow_yaml_remote_backend_fixture(request):
    launchflow_yaml_mock = mock_launchflow_yaml_remote_backend()
    launchflow_yaml_mock.start()
    request.cls.launchflow_yaml = launchflow_yaml_mock.launchflow_yaml
    yield launchflow_yaml_mock
    launchflow_yaml_mock.stop()
