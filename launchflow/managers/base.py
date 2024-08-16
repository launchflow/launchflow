from typing import Union

from launchflow.backend import GCSBackend, LaunchFlowBackend, LocalBackend


class BaseManager:
    def __init__(
        self,
        backend: Union[LocalBackend, LaunchFlowBackend, GCSBackend],
    ) -> None:
        self.backend = backend
