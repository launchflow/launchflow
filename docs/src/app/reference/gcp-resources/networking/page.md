## FirewallAllowRule

A GCP firewall allow rule.

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

### initialization

Create a new firewall allow rule.

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

## AllowRule

Allow rule for allowing certain traffic through a VPC firewall.

Attributes:
- `protocol: (Literal["tcp", "udp", "icmp", "esp", "ah", "sctp", "all"])`: The protocol to allow.
- `ports: Optional[List[int]]`: The ports to allow traffic on. If not provided, all ports are allowed.
