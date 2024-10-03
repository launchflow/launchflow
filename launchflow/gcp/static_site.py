import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import IO, List, Optional

from pathspec import PathSpec

from launchflow import exceptions
from launchflow.config import config
from launchflow.gcp.gcs import BackendBucket
from launchflow.gcp.service import GCPService
from launchflow.models.enums import ServiceProduct
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DNSOutputs, DNSRecord, ServiceOutputs


async def deploy_local_files_to_gcs_static_site(
    gcp_environment_config: GCPEnvironmentConfig,
    bucket_name: str,
    static_directory: str,
    url_map_resource_id: str,
    wait_for_cdn_invalidation: bool,
):
    try:
        import google.auth
        import google.auth.transport.requests
        from google.cloud import storage  # type: ignore
        from googleapiclient.discovery import build
    except ImportError:
        raise exceptions.MissingGCPDependency()

    bucket = storage.Client().get_bucket(bucket_name)

    local_dir = os.path.join(
        os.path.dirname(os.path.abspath(config.launchflow_yaml.config_path)),
        static_directory,
    )

    def should_include_file(pathspec: PathSpec, file_path: str, root_dir: str):
        relative_path = os.path.relpath(file_path, root_dir)
        return not pathspec.match_file(relative_path)

    for root, _, files in os.walk(local_dir):
        for file in files:
            file_path = os.path.join(root, file)
            blob = bucket.blob(os.path.relpath(file_path, local_dir))
            blob.upload_from_filename(file_path)

    # Authenticate with the docker registry
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore

    # Build the Compute Engine service object
    compute_service = build("compute", "v1", credentials=creds)

    # Invalidate the cache for the specified URL map
    request_body = {
        "path": "/*",
    }
    request_id = str(uuid.uuid4())  # Generate a unique request ID

    url_map_name = url_map_resource_id.split("/")[-1]
    # Perform the cache invalidation request
    operation = (
        compute_service.urlMaps()
        .invalidateCache(
            project=gcp_environment_config.project_id,  # type: ignore
            urlMap=url_map_name,
            body=request_body,
            requestId=request_id,
        )
        .execute()
    )

    if wait_for_cdn_invalidation:
        while True:
            result = (
                compute_service.globalOperations()
                .get(
                    project=gcp_environment_config.project_id,
                    operation=operation["name"],
                )
                .execute()
            )

            if result["status"] == "DONE":
                if "error" in result:
                    raise Exception(f"Operation failed with errors: {result['error']}")
                break
            await asyncio.sleep(5)


@dataclass
class GCSStaticSiteInputs(Inputs):
    static_directory: str


# TODO: Add docs
class GCSStaticSite(GCPService[None]):
    """A static website hosted on Google Cloud Storage and served through a CDN.

    ### Example Usage
    ```python
    import launchflow as lf

    website = lf.gcp.GCSStaticSite("my-website", build_directory="path/to/local/files")
    ```
    """

    product = ServiceProduct.GCP_STATIC_SITE.value

    def __init__(
        self,
        name: str,
        static_directory: str,
        *,
        build_command: Optional[str] = None,
        build_directory: str = ".",
        build_ignore: List[str] = [],
        wait_for_cdn_invalidation: bool = False,
        # backend bucket inputs
        region: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Creates a new Cloud Run service.

        **Args:**
        - `name (str)`: The name of the service.
        - `static_directory (str)`: The directory of static files to serve. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_command (Optional[str])`: The command to run to build the static files. If not provided, the files will be served as is.
        - `build_directory (str)`: The directory of static files to serve. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_ignore (List[str])`: A list of files to ignore when deploying the service. This can be in the same syntax you would use for a `.gitignore`.
        - `region (Optional[str])`: The region to deploy the service to.
        - `domain (Optional[str])`: The custom domain to map to the service.
        """
        build_diff_args = {}
        if build_command is not None:
            build_diff_args["build_command"] = build_command
        super().__init__(
            name=name,
            build_directory=build_directory,
            build_ignore=build_ignore,
            build_diff_args=build_diff_args,
        )
        self.static_directory = static_directory
        self.build_command = build_command
        self.wait_for_cdn_invalidation = wait_for_cdn_invalidation
        self.region = region
        self.domain = domain

        # TODO: make this configurable
        self._backend_bucket = BackendBucket(
            name=name,
            force_destroy=True,
            custom_domain=domain,
            main_page_suffix="index.html",
            not_found_page="404.html",
        )

    def inputs(self) -> GCSStaticSiteInputs:
        return GCSStaticSiteInputs(static_directory=self.static_directory)

    def resources(self) -> List[Resource]:
        return [self._backend_bucket]

    def outputs(self) -> ServiceOutputs:
        try:
            backend_bucket_outputs = self._backend_bucket.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        service_url = f"http://{backend_bucket_outputs.cdn_ip_address}"
        dns_outputs = None

        if self.domain:
            service_url = f"https://{self.domain}"
            dns_outputs = DNSOutputs(
                domain=self.domain,
                dns_records=[
                    DNSRecord(
                        dns_record_value=backend_bucket_outputs.cdn_ip_address,
                        dns_record_type="A",
                    ),
                ],
            )

        service_outputs = ServiceOutputs(
            service_url=service_url,
            dns_outputs=dns_outputs,
        )
        service_outputs.gcp_id = backend_bucket_outputs.gcp_id

        return service_outputs

    async def _build(
        self,
        *,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        build_log_file: IO,
        build_local: bool,
    ) -> None:
        if self.build_command is not None:
            build_log_file.write(f"Running build command: {self.build_command}")
            process = await asyncio.create_subprocess_shell(
                self.build_command,
                stdout=build_log_file,
                stderr=build_log_file,
                cwd=self.build_directory,
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                raise exceptions.BuildFailed(self.name)
        else:
            build_log_file.write(
                f"No build command provided. Serving static files in {self.static_directory}"
            )

    async def _promote(
        self,
        *,
        from_gcp_environment_config: GCPEnvironmentConfig,
        to_gcp_environment_config: GCPEnvironmentConfig,
        from_launchflow_uri: LaunchFlowURI,
        to_launchflow_uri: LaunchFlowURI,
        from_deployment_id: str,
        to_deployment_id: str,
        promote_log_file: IO,
        promote_local: bool,
    ) -> None:
        # TODO: Implement the promote flow (super will raise NotImplementedError)
        return await super()._promote(
            from_gcp_environment_config=from_gcp_environment_config,
            to_gcp_environment_config=to_gcp_environment_config,
            from_launchflow_uri=from_launchflow_uri,
            to_launchflow_uri=to_launchflow_uri,
            from_deployment_id=from_deployment_id,
            to_deployment_id=to_deployment_id,
            promote_log_file=promote_log_file,
            promote_local=promote_local,
        )

    async def _release(
        self,
        *,
        release_inputs: None,
        gcp_environment_config: GCPEnvironmentConfig,
        launchflow_uri: LaunchFlowURI,
        deployment_id: str,
        release_log_file: IO,
    ):
        backend_bucket_outputs = self._backend_bucket.outputs()
        result = await deploy_local_files_to_gcs_static_site(
            gcp_environment_config=gcp_environment_config,
            bucket_name=backend_bucket_outputs.bucket_name,
            static_directory=self.static_directory,
            url_map_resource_id=backend_bucket_outputs.url_map_resource_id,
            wait_for_cdn_invalidation=self.wait_for_cdn_invalidation,
        )
        release_log_file.write(f"Deployed to {result}")
