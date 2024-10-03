import asyncio
import gzip
import hashlib
import io
import os
from dataclasses import dataclass
from typing import IO, List, Optional

import requests

from launchflow import exceptions
from launchflow.gcp.firebase import FirebaseHostingSite, FirebaseProject
from launchflow.gcp.service import GCPService
from launchflow.models.enums import ServiceProduct
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.models.launchflow_uri import LaunchFlowURI
from launchflow.node import Inputs
from launchflow.resource import Resource
from launchflow.service import DNSOutputs, DNSRecord, ServiceOutputs


# Followed these docs: https://firebase.google.com/docs/hosting/api-deploy
async def deploy_local_files_to_firebase_static_site(
    gcp_environment_config: GCPEnvironmentConfig,
    firebase_site_id: str,
    static_directory: str,
):
    try:
        import google.auth
        import google.auth.transport.requests
        from googleapiclient.discovery import build
    except ImportError:
        raise exceptions.MissingGCPDependency()

    # Authenticate with the docker registry
    creds, _ = google.auth.default(
        quota_project_id=gcp_environment_config.project_id,  # type: ignore
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore

    # Build the Firebase Hosting service object
    firebase_service = build("firebasehosting", "v1beta1", credentials=creds)

    # Create a new version of the Firebase Hosting site
    request_body = {
        "config": {
            "rewrites": [
                {
                    "glob": "**",
                    "path": "/index.html",
                }
            ],
        },
    }
    create_version_response = (
        firebase_service.sites()
        .versions()
        .create(
            parent=f"sites/{firebase_site_id}",
            body=request_body,
        )
        .execute()
    )

    # Extract the VERSION_ID from the response
    version_name = create_version_response.get("name")
    VERSION_ID = version_name.split("/")[-1] if version_name else None

    if not VERSION_ID:
        raise ValueError("Failed to create a new version. VERSION_ID not found.")

    # Function to compress a file in memory and calculate its SHA256 hash
    def gzip_and_hash_file(file_path):
        # Open the file and compress it in memory
        with open(file_path, "rb") as f:
            file_data = f.read()
            compressed_file = io.BytesIO()
            with gzip.GzipFile("", "wb", 9, compressed_file, 0.0) as gz:
                gz.write(file_data)

            compressed_file.seek(0)
            compressed_data = compressed_file.read()

        # Calculate the SHA256 hash of the compressed file
        file_hash = hashlib.sha256(compressed_data).hexdigest()

        return file_hash, compressed_data

    # Dictionary to hold the paths and their respective hashes
    files_to_deploy = {}

    # Walk the directory tree and process each file
    for root, _, files in os.walk(static_directory):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash, _ = gzip_and_hash_file(file_path)
            relative_path = os.path.relpath(file_path, static_directory)
            files_to_deploy[f"/{relative_path}"] = file_hash

    # Step 4: Populate files for the new version
    populate_files_request_body = {"files": files_to_deploy}

    # Make the API request to populate the files
    populate_files_response = (
        firebase_service.sites()
        .versions()
        .populateFiles(
            parent=f"sites/{firebase_site_id}/versions/{VERSION_ID}",
            body=populate_files_request_body,
        )
        .execute()
    )

    # Extract the upload required hashes and the upload URL from the response
    upload_required_hashes = populate_files_response.get("uploadRequiredHashes", [])
    upload_url = populate_files_response.get("uploadUrl")

    # Step 5: Upload required files
    for file_path, file_hash in files_to_deploy.items():
        if file_hash in upload_required_hashes:
            # Generate the file-specific upload URL
            file_upload_url = f"{upload_url}/{file_hash}"

            # Get the compressed data for this file
            _, compressed_data = gzip_and_hash_file(
                os.path.join(static_directory, file_path.lstrip("/"))
            )

            # Upload the file
            headers = {
                "Authorization": f"Bearer {creds.token}",  # type: ignore
                "Content-Type": "application/octet-stream",
            }
            response = requests.post(
                file_upload_url, headers=headers, data=compressed_data
            )

            if response.status_code != 200:
                raise ValueError(
                    f"Failed to upload {file_path}: {response.status_code} - {response.text}"
                )

    # Step 6: Update the status of the version to FINALIZED
    finalize_version_request_body = {"status": "FINALIZED"}

    # Make the API request to finalize the version
    finalize_response = (
        firebase_service.sites()
        .versions()
        .patch(
            name=f"sites/{firebase_site_id}/versions/{VERSION_ID}",
            updateMask="status",
            body=finalize_version_request_body,
        )
        .execute()
    )

    if finalize_response.get("status") != "FINALIZED":
        raise ValueError(f"Failed to finalize version {VERSION_ID}")

    # Step 7: Release the version for deployment
    release_request_body = {}  # type: ignore

    # Make the API request to create a release
    _ = (
        firebase_service.sites()
        .releases()
        .create(
            parent=f"sites/{firebase_site_id}",
            versionName=f"sites/{firebase_site_id}/versions/{VERSION_ID}",
            body=release_request_body,
        )
        .execute()
    )


@dataclass
class FirebaseStaticSiteInputs(Inputs):
    static_directory: str


class FirebaseStaticSite(GCPService[None]):
    """A service hosted on Firebase Hosting.

    ### Example Usage
    ```python
    import launchflow as lf

    website = lf.gcp.FirebaseStaticSite("my-website", build_directory="path/to/local/files")
    ```
    """

    product = ServiceProduct.GCP_FIREBASE_STATIC_SITE.value

    def __init__(
        self,
        name: str,
        static_directory: str,
        *,
        build_command: Optional[str] = None,
        build_directory: str = ".",
        build_ignore: List[str] = [],
        # backend bucket inputs
        region: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> None:
        """Creates a new Firebase Static Site service.

        **Args:**
        - `name (str)`: The name of the service.
        - `static_directory (str)`: The directory of static files to serve. This should be a relative path from the project root where your `launchflow.yaml` is defined.
        - `build_command (Optional[str])`: The command to run to build the static files. If not provided, the files will be served as is.
        - `build_directory (str)`: The directory to run the build command in. This should be a relative path from the project root where your `launchflow.yaml` is defined.
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
        self.region = region
        self.domain = domain

        self._firebase_project = FirebaseProject(name=f"{name}-firebase-project")
        self._firebase_hosting_site = FirebaseHostingSite(
            name=f"{name}-firebase-site",
            firebase_project=self._firebase_project,
            custom_domain=domain,
        )

    def inputs(self) -> FirebaseStaticSiteInputs:
        return FirebaseStaticSiteInputs(static_directory=self.static_directory)

    def resources(self) -> List[Resource]:
        return [
            self._firebase_project,
            self._firebase_hosting_site,
        ]

    def outputs(self) -> ServiceOutputs:
        try:
            firebase_hosting_outputs = self._firebase_hosting_site.outputs()
        except exceptions.ResourceOutputsNotFound:
            raise exceptions.ServiceOutputsNotFound(service_name=self.name)

        dns_outputs = None
        if firebase_hosting_outputs.desired_dns_records and self.domain is not None:
            dns_records = []
            for record in firebase_hosting_outputs.desired_dns_records:
                dns_type, dns_value = record.split(",", 1)
                dns_records.append(
                    DNSRecord(
                        dns_record_value=dns_value,
                        dns_record_type=dns_type,  # type: ignore
                    ),
                )
            dns_outputs = DNSOutputs(
                domain=self.domain,
                dns_records=dns_records,
            )

        service_url = firebase_hosting_outputs.default_url
        if self.domain:
            service_url = f"https://{self.domain}"

        service_outputs = ServiceOutputs(
            service_url=service_url,
            dns_outputs=dns_outputs,
        )
        service_outputs.gcp_id = firebase_hosting_outputs.gcp_id

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
        # We need to move the firebase build step out of the release step and into the build / promote step
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
        result = await deploy_local_files_to_firebase_static_site(
            gcp_environment_config=gcp_environment_config,
            firebase_site_id=self._firebase_hosting_site.resource_id,  # TODO: Get this from outputs
            static_directory=self.static_directory,
        )
        release_log_file.write(f"Deployed to {result}")
