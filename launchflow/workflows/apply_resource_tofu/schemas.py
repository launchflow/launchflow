from dataclasses import dataclass
from typing import Optional


@dataclass
class ApplyResourceTofuOutputs:
    gcp_id: Optional[str]
    aws_arn: Optional[str]
