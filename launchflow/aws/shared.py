from dataclasses import dataclass, field
from typing import List

from launchflow.node import Inputs


@dataclass
class CORS(Inputs):
    """
    Cross-Origin Resource Sharing (CORS) configuration.

    **Args:**
    - `allow_credentials (bool)`: Whether to allow credentials.
    - `allow_origins (List[str])`: A list of allowed origins.
    - `allow_methods (List[str])`: A list of allowed methods.
    - `allow_headers (List[str])`: A list of allowed headers.
    - `expose_headers (List[str])`: A list of headers to expose.
    - `max_age (int)`: The maximum age of the preflight request.
    """

    allow_credentials: bool = False
    allow_origins: List[str] = field(default_factory=lambda: ["*"])
    allow_methods: List[str] = field(default_factory=lambda: ["*"])
    allow_headers: List[str] = field(default_factory=lambda: ["keep-alive", "date"])
    expose_headers: List[str] = field(default_factory=lambda: ["keep-alive", "date"])
    max_age: int = 86400  # 24 hours
