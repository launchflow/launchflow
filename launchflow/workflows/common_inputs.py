from dataclasses import dataclass
from typing import Optional


@dataclass
class DockerBuildInputs:
    source_tarball_bucket: Optional[str]
    source_tarball_path: Optional[str]
    dockerfile_path: Optional[str]
    local_source_dir: str
