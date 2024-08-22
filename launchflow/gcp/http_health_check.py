import dataclasses
from typing import Literal, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class HealthCheckInputs(ResourceInputs):
    check_interval_sec: int
    timeout_sec: int
    healthy_threshold: int
    unhealthy_threshold: int
    host: Optional[str]
    request_path: str
    port: int
    response: Optional[str]
    proxy_header: Optional[Literal["NONE", "PROXY_V1"]]
    port_specification: Optional[
        Literal["USE_SERVING_PORT", "USE_FIXED_PORT", "USE_SSL_PORT"]
    ]


@dataclasses.dataclass
class HealthCheckOutputs(Outputs):
    pass


class HttpHealthCheck(GCPResource[HealthCheckOutputs]):
    """A health check for a managed instance group.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/load-balancing/docs/health-check-concepts).

    ### Example Usage

    #### Basic Usage
    ```python
    import launchflow as lf

    health_check = lf.gcp.HttpHealthCheck("health-check")
    ```

    #### With customization
    ```python
    import launchflow as lf

    health_check = lf.gcp.HttpHealthCheck(
        "health-check",
        request_path="/healthz",
        port=8080,
        check_interval_sec=10,
        timeout_sec=10,
        healthy_threshold=3,
        unhealthy_threshold=4,
    )
    ```
    """

    product = ResourceProduct.GCP_COMPUTE_HTTP_HEALTH_CHECK.value

    def __init__(
        self,
        name,
        *,
        check_interval_sec: int = 5,
        timeout_sec: int = 5,
        healthy_threshold: int = 2,
        unhealthy_threshold: int = 3,
        host: Optional[str] = None,
        request_path: str = "/",
        port: int = 80,
        response: Optional[str] = None,
        proxy_header: Optional[Literal["NONE", "PROXY_V1"]] = None,
        port_specification: Optional[
            Literal["USE_SERVING_PORT", "USE_FIXED_PORT", "USE_NAMED_PORT"]
        ] = None,
    ):
        """Create a new HttpHealthCheck.

        **Args:**
        - `name (str)`: The name of the health check.
        - `check_interval_sec (int)`: How often to check the health of the backend.
        - `timeout_sec (int)`: How long to wait for a response before failing the check.
        - `healthy_threshold (int)`: How many successful checks before marking the backend as healthy.
        - `unhealthy_threshold (int)`: How many failed checks before marking the backend as unhealthy.
        - `host (str)`: The host header to send with the request. Defauls to the VM attached to the instance.
        - `request_path (str)`: The path to send the request to. Defaults to `/`.
        - `port (int)`: The port to send the request to. Defaults to `80`.
        - `response (str)`: The expected response from the backend. Defaults to `None`.
        - `proxy_header (str)`: The proxy header to send with the request. Defaults to `None`.
        - `port_specification (str)`: The port specification to use. Defaults to `None`.
        """
        super().__init__(name)
        self.name = name
        self.check_interval_sec = check_interval_sec
        self.timeout_sec = timeout_sec
        self.healthy_threshold = healthy_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self.host = host
        self.request_path = request_path
        self.port = port
        self.response = response
        self.proxy_header = proxy_header
        self.port_specification = port_specification

    def inputs(self, environment_state: EnvironmentState) -> HealthCheckInputs:
        return HealthCheckInputs(
            resource_id=self.resource_id,
            check_interval_sec=self.check_interval_sec,
            timeout_sec=self.timeout_sec,
            healthy_threshold=self.healthy_threshold,
            unhealthy_threshold=self.unhealthy_threshold,
            host=self.host,
            request_path=self.request_path,
            port=self.port,
            response=self.response,
            proxy_header=self.proxy_header,  # type: ignore
            port_specification=self.port_specification,  # type: ignore
        )
