import dataclasses
from typing import List, Literal, Optional

from launchflow.gcp.resource import GCPResource
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class AllowRule(Inputs):
    """Allow rule for allowing certain traffic through a VPC firewall.

    Attributes:
    - `protocol: (Literal["tcp", "udp", "icmp", "esp", "ah", "sctp", "all"])`: The protocol to allow.
    - `ports: Optional[List[int]]`: The ports to allow traffic on. If not provided, all ports are allowed.
    """

    protocol: Literal["tcp", "udp", "icmp", "esp", "ah", "sctp", "all"]
    ports: Optional[List[int]] = None


@dataclasses.dataclass
class FirewallAllowRuleInputs(ResourceInputs):
    source_ranges: Optional[List[str]]
    source_tags: Optional[List[str]]
    direction: Literal["INGRESS", "EGRESS"]
    priority: int
    target_service_accounts: Optional[List[str]]
    target_tags: Optional[List[str]]
    description: Optional[str]
    allow_rules: Optional[List[AllowRule]]


@dataclasses.dataclass
class FirewallRuleOutputs(Outputs):
    pass


class FirewallAllowRule(GCPResource[FirewallRuleOutputs]):
    """A GCP firewall allow rule.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/firewall/docs/firewalls).

    ### Example Usage

    ```python
    import launchflow as lf

    firewall_rule = lf.gcp.FirewallAllowRule(
        "fw-rule",
        direction="INGRESS",
        allow_rules=[
            lf.gcp.AllowRule(protocol="tcp", ports=[80])
        ])
    ```
    """

    product = ResourceProduct.GCP_FIREWALL_ALLOW_RULE.value

    def __init__(
        self,
        name: str,
        *,
        direction: Literal["INGRESS", "EGRESS"],
        allow_rules: Optional[List[AllowRule]] = None,
        source_ranges: Optional[List[str]] = None,
        source_tags: Optional[List[str]] = None,
        priority: int = 1000,
        target_service_accounts: Optional[List[str]] = None,
        target_tags: Optional[List[str]] = None,
        destination_ranges: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        """Create a new firewall allow rule.

        **Args:**
        - `name (str)`: The name of the firewall rule.
        - `direction (Literal["INGRESS", "EGRESS"])`: The direction of the rule.
        - `allow_rules (Optional[List[AllowRule]])`: The [allow rules](#allow-rule) for the firewall rule.
        - `source_ranges (Optional[List[str]])`: The source ranges for the firewall rule.
        - `source_tags (Optional[List[str]])`: The source tags for the firewall rule.
        - `priority (int)`: The priority of the firewall rule.
        - `target_service_accounts (Optional[List[str]])`: The target service accounts for the firewall rule.
        - `target_tags (Optional[List[str]])`: The target tags for the firewall rule.
        - `destination_ranges (Optional[List[str]])`: The destination ranges for the firewall rule.
        - `description (Optional[str])`: The description of the firewall rule.
        """
        super().__init__(name)
        self.direction = direction
        self.source_ranges = source_ranges
        self.source_tags = source_tags
        self.priority = priority
        self.target_service_accounts = target_service_accounts
        self.target_tags = target_tags
        self.destination_ranges = destination_ranges
        self.description = description
        self.allow_rules = allow_rules

        if (
            direction == "INGRESS"
            and not source_tags
            and not source_ranges
            and not source_tags
        ):
            raise ValueError(
                "Ingress rules must contain at least one source range or tag"
            )
        if direction == "EGRESS" and not destination_ranges:
            raise ValueError("Egress rules must contain at least one destination range")

    def inputs(self, environment_state: EnvironmentState) -> FirewallAllowRuleInputs:
        return FirewallAllowRuleInputs(
            resource_id=self.resource_id,
            source_ranges=self.source_ranges,
            source_tags=self.source_tags,
            direction=self.direction,  # type: ignore
            priority=self.priority,
            target_service_accounts=self.target_service_accounts,
            target_tags=self.target_tags,
            description=self.description,
            allow_rules=self.allow_rules,
        )
