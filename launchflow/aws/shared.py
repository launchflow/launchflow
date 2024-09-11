from dataclasses import dataclass, field
from typing import List

from launchflow.node import Inputs


@dataclass
class CORS(Inputs):
    allow_credentials: bool = False
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["keep-alive", "date"])
    expose_headers: List[str] = field(default_factory=lambda: ["keep-alive", "date"])
    max_age: int = 86400  # 24 hours
