import asyncio
import gzip
import hashlib
import io
import json
import os
import time
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Tuple

import requests
from docker.errors import APIError, BuildError
from kubernetes import config as k8_config
from pathspec import PathSpec

from launchflow import exceptions
from launchflow.config import config
from launchflow.gcp.cloud_run import CloudRunService
from launchflow.gcp.compute_engine_service import ComputeEngineService
from launchflow.gcp.firebase_site import FirebaseStaticSite
from launchflow.gcp.gke_service import GKEService
from launchflow.gcp.service import GCPDockerService
from launchflow.gcp.static_site import GCSWebsite
from launchflow.managers.service_manager import ServiceManager
from launchflow.models.flow_state import GCPEnvironmentConfig, ServiceState
from launchflow.workflows.k8s_service import update_k8s_service
from launchflow.workflows.utils import tar_source_in_memory

4
if TYPE_CHECKING:
    from google.cloud.container import Cluster


async def _upload_source_tarball_to_gcs(
    source_tarball_gcs_path: str,
    artifact_bucket: str,
    local_source_dir: str,
    build_ignore: List[str],
):
    try:
        from google.cloud import storage  # type: ignore
    except ImportError:
        raise exceptions.MissingGCPDependency()

    def upload_async():
        source_tarball = tar_source_in_memory(local_source_dir, build_ignore)
        try:
            bucket = storage.Client().get_bucket(artifact_bucket)
            blob = bucket.blob(source_tarball_gcs_path)
            blob.upload_from_file(source_tarball)
        except Exception:
            raise exceptions.UploadSrcTarballFailed()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, upload_async)


async def _run_docker_gcp_cloud_build(
    docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    gcs_source_bucket: str,
    gcs_source_object: str,
    gcp_project_id: str,
    dockerfile_path: str,
    artifact_bucket: str,
    service_account_email: str,
):
    try:
        from google.cloud.devtools import cloudbuild_v1
    except ImportError:
        raise exceptions.MissingGCPDependency()

    latest_image_name = f"{docker_repository}/{docker_image_name}:latest"
    tagged_image_name = f"{docker_repository}/{docker_image_name}:{docker_image_tag}"

    # Create the Cloud Build build plan
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=gcs_source_bucket, object_=gcs_source_object
            )
        ),
        service_account=f"projects/{gcp_project_id}/serviceAccounts/{service_account_email}",
        logs_bucket=f"gs://{artifact_bucket}/logs/cloud-builds",
        steps=[
            # Pull the latest image from the registry to use as a cache
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                entrypoint="bash",
                args=[
                    "-c",
                    f"docker pull {latest_image_name} || exit 0",
                ],
            ),
            # Build the docker image with the cache from the latest image
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                args=[
                    "build",
                    "-t",
                    latest_image_name,
                    "-t",
                    tagged_image_name,
                    "--cache-from",
                    latest_image_name,
                    "-f",
                    dockerfile_path,
                    ".",
                ],
            ),
        ],
        # NOTE: This is what pushes the image to the registry
        images=[latest_image_name, tagged_image_name],
    )
    # Submit the build to Cloud Build
    cloud_build_client = cloudbuild_v1.CloudBuildAsyncClient()
    operation = await cloud_build_client.create_build(
        project_id=gcp_project_id,
        build=build,
        timeout=3600,  # 1 hour timeout
    )
    build_url = f"https://console.cloud.google.com/cloud-build/builds/{operation.metadata.build.id}?project={gcp_project_id}"
    # Add logs to the table to the table
    try:
        # For some reason timeout=None is not working, so we set it to 1 hour
        await operation.result(timeout=3600)
    except Exception as e:
        raise exceptions.ServiceBuildFailed(
            error_message=str(e), build_logs_or_link=build_url
        )

    # Return the docker image name
    return tagged_image_name, build_url


def _write_build_logs(file_path: str, log_stream):
    with open(file_path, "a") as f:
        for chunk in log_stream:
            if "stream" in chunk:
                f.write(chunk["stream"])
            if "status" in chunk:
                f.write(chunk["status"] + "\n")


# TODO: Look into cleaning up old images. I noticed my docker images were taking up a lot of space
# after running this workflow multiple times
async def _build_docker_image_local(
    docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    local_source_dir: str,
    dockerfile_path: str,
    build_logs_file: str,
):
    try:
        from docker import errors, from_env  # type: ignore
    except ImportError:
        raise exceptions.MissingDockerDependency()
    try:
        import google.auth
        import google.auth.transport.requests

    except ImportError:
        raise exceptions.MissingGCPDependency()

    docker_client = from_env()
    latest_image_name = f"{docker_repository}/{docker_image_name}:latest"
    tagged_image_name = f"{docker_repository}/{docker_image_name}:{docker_image_tag}"
    # Authenticate with the docker registry
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    docker_client.login(
        username="oauth2accesstoken",
        password=creds.token,
        registry=f"https://{docker_repository.split('/')[0]}",
    )

    # Pull the latest image from the registry to use as a cache
    try:
        # TODO: This is throwing a 500 error saying unauthorized
        docker_client.images.pull(latest_image_name)
        cache_from = [latest_image_name]
    except errors.NotFound:
        # NOTE: this happens on the first build
        cache_from = []

    # Build the docker image with the cache from the latest image
    loop = asyncio.get_event_loop()
    try:
        _, log_stream = await loop.run_in_executor(
            None,
            lambda: docker_client.images.build(
                path=os.path.dirname(local_source_dir),
                dockerfile=dockerfile_path,
                tag=tagged_image_name,
                cache_from=cache_from,
                # NOTE: this is required to build on mac
                platform="linux/amd64",
            ),
        )
        _write_build_logs(build_logs_file, log_stream)
    except BuildError as e:
        _write_build_logs(build_logs_file, e.build_log)
        raise exceptions.ServiceBuildFailed(
            error_message=str(e), build_logs_or_link=build_logs_file
        )

    # Tag as latest
    docker_client.images.get(tagged_image_name).tag(latest_image_name)

    # Push the images to the registry
    docker_client.images.push(tagged_image_name)
    docker_client.images.push(latest_image_name)

    # Return the docker image name
    return tagged_image_name


async def _promote_docker_image(
    source_env_region: str,
    source_docker_image: str,
    target_docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    target_gcp_project_id: str,
    target_artifact_bucket: str,
    target_service_account_email: str,
):
    try:
        import google.auth
        import google.auth.transport.requests
        from google.cloud.devtools import cloudbuild_v1
    except ImportError:
        raise exceptions.MissingGCPDependency()

    target_image = f"{target_docker_repository}/{docker_image_name}"
    tagged_target_image = f"{target_image}:{docker_image_tag}"
    latest_target_image = f"{target_image}:latest"

    # Fetch creds to use for pulling the source image in the target's project
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())

    build = cloudbuild_v1.Build(
        service_account=f"projects/{target_gcp_project_id}/serviceAccounts/{target_service_account_email}",
        logs_bucket=f"gs://{target_artifact_bucket}/logs/cloud-builds",
        steps=[
            # Pull the latest image from the registry to use as a cache
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                entrypoint="bash",
                args=[
                    "-c",
                    (
                        f"echo {creds.token} | docker login --username=oauth2accesstoken --password-stdin https://{source_env_region}-docker.pkg.dev "
                        f"&& docker pull {source_docker_image} "
                        f"&& docker tag {source_docker_image} {target_image}:{docker_image_tag} "
                        f"&& docker tag {source_docker_image} {target_image}:latest"
                    ),
                ],
            ),
        ],
        # NOTE: This is what pushes the image to the registry
        images=[target_image, tagged_target_image, latest_target_image],
    )
    # Submit the build to Cloud Build
    cloud_build_client = cloudbuild_v1.CloudBuildAsyncClient()
    operation = await cloud_build_client.create_build(
        project_id=target_gcp_project_id,
        build=build,
        timeout=3600,  # 1 hour timeout
    )
    build_url = f"https://console.cloud.google.com/cloud-build/builds/{operation.metadata.build.id}?project={target_gcp_project_id}"
    try:
        # For some reason timeout=None is not working, so we set it to 1 hour
        await operation.result(timeout=3600)
    except Exception as e:
        raise exceptions.ServicePromoteFailed(
            error_message=str(e), promote_logs_or_link=build_url
        )

    # Return the docker image name
    return tagged_target_image, build_url


async def _promote_docker_image_local(
    source_service_region: str,
    source_docker_image: str,
    target_docker_repository: str,
    target_service_region: str,
    docker_image_name: str,
    docker_image_tag: str,
):
    target_image = f"{target_docker_repository}/{docker_image_name}"
    tagged_target_image = f"{target_image}:{docker_image_tag}"

    try:
        import google.auth
        import google.auth.transport.requests
    except ImportError:
        raise exceptions.MissingGCPDependency()
    try:
        from docker import from_env  # type: ignore
    except ImportError:
        raise exceptions.MissingDockerDependency()

    # Fetch creds to use for pulling the source image in the target's project
    source_token = os.environ.get("SOURCE_ENV_DOCKER_TOKEN")
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    if source_token is None:
        source_token = creds.token

    base_logging_dir = "/tmp/launchflow"
    os.makedirs(base_logging_dir, exist_ok=True)
    full_log_file = os.path.join(base_logging_dir, f"promote_{docker_image_tag}.log")

    def promote_image():
        docker_client = from_env()
        docker_client.login(
            username="oauth2accesstoken",
            password=source_token,
            registry=f"https://{source_service_region}-docker.pkg.dev",
        )
        try:
            image = docker_client.images.pull(source_docker_image)
        except APIError:
            sa_email = None
            if hasattr(creds, "service_account_email"):
                sa_email = creds.service_account_email
            raise exceptions.GCPDockerPullFailed(
                service_account_email=sa_email, docker_image=source_docker_image
            )
        image.tag(target_image, docker_image_tag)
        image.tag(target_image, "latest")
        output = docker_client.images.push(
            target_image, docker_image_tag, stream=True, decode=True
        )
        _write_build_logs(full_log_file, output)
        output = docker_client.images.push(
            target_image, "latest", stream=True, decode=True
        )
        _write_build_logs(full_log_file, output)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, promote_image)
    # Return the docker image name
    return tagged_target_image, full_log_file


async def build_and_push_gcp_service(
    gcp_service: GCPDockerService,
    service_manager: ServiceManager,
    gcp_environment_config: GCPEnvironmentConfig,
    deployment_id: str,
    build_local: bool,
) -> Tuple[str, str]:
    if build_local:
        return await build_gcp_service_locally(
            gcp_service=gcp_service,
            service_manager=service_manager,
            deployment_id=deployment_id,
        )
    return await build_docker_image_on_cloud_build(
        gcp_service=gcp_service,
        service_manager=service_manager,
        gcp_environment_config=gcp_environment_config,
        deployment_id=deployment_id,
    )


async def build_docker_image_on_cloud_build(
    gcp_service: GCPDockerService,
    service_manager: ServiceManager,
    gcp_environment_config: GCPEnvironmentConfig,
    deployment_id: str,
) -> Tuple[str, str]:
    full_yaml_path = os.path.dirname(
        os.path.abspath(config.launchflow_yaml.config_path)
    )
    local_source_dir = os.path.join(full_yaml_path, gcp_service.build_directory)
    source_tarball_gcs_path = f"builds/{service_manager.project_name}/{service_manager.environment_name}/services/{service_manager.service_name}/source.tar.gz"
    # Step 1 - Upload the source tarball to GCS
    await _upload_source_tarball_to_gcs(
        source_tarball_gcs_path=source_tarball_gcs_path,
        artifact_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
        local_source_dir=local_source_dir,
        build_ignore=gcp_service.build_ignore,
    )

    service_outputs = gcp_service.outputs()

    # Step 2 - Build and push the docker image
    docker_image, build_url = await _run_docker_gcp_cloud_build(
        docker_repository=service_outputs.docker_repository,
        docker_image_name=service_manager.service_name,
        docker_image_tag=deployment_id,
        gcs_source_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
        gcs_source_object=source_tarball_gcs_path,
        gcp_project_id=gcp_environment_config.project_id,  # type: ignore
        dockerfile_path=gcp_service.dockerfile,
        artifact_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
        service_account_email=gcp_environment_config.service_account_email,  # type: ignore
    )

    return docker_image, build_url


async def build_gcp_service_locally(
    gcp_service: GCPDockerService,
    service_manager: ServiceManager,
    deployment_id: str,
) -> Tuple[str, str]:
    full_yaml_path = os.path.dirname(
        os.path.abspath(config.launchflow_yaml.config_path)
    )
    local_source_dir = os.path.join(full_yaml_path, gcp_service.build_directory)

    service_outputs = gcp_service.outputs()

    base_logging_dir = "/tmp/launchflow"
    os.makedirs(base_logging_dir, exist_ok=True)
    build_logs_file = (
        f"{base_logging_dir}/{service_manager.service_name}-{int(time.time())}.log"
    )

    # Step 1 - Build and push the docker image
    docker_image = await _build_docker_image_local(
        docker_repository=service_outputs.docker_repository,
        docker_image_name=service_manager.service_name,
        docker_image_tag=deployment_id,
        local_source_dir=local_source_dir,
        dockerfile_path=gcp_service.dockerfile,
        build_logs_file=build_logs_file,
    )

    return docker_image, build_logs_file


async def upload_local_files_to_static_site(
    gcp_environment_config: GCPEnvironmentConfig,
    static_site: GCSWebsite,
):
    try:
        import google.auth
        import google.auth.transport.requests
        from google.cloud import storage  # type: ignore
        from googleapiclient.discovery import build
    except ImportError:
        raise exceptions.MissingGCPDependency()

    service_url = static_site.outputs().service_url
    backend_bucket_outputs = static_site._backend_bucket.outputs()
    bucket = storage.Client().get_bucket(backend_bucket_outputs.bucket_name)

    local_dir = os.path.join(
        os.path.dirname(os.path.abspath(config.launchflow_yaml.config_path)),
        static_site.build_directory,
    )

    def should_include_file(pathspec: PathSpec, file_path: str, root_dir: str):
        relative_path = os.path.relpath(file_path, root_dir)
        return not pathspec.match_file(relative_path)

    pathspec = PathSpec.from_lines("gitwildmatch", static_site.build_ignore)
    for root, _, files in os.walk(local_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if should_include_file(pathspec, file_path, local_dir):
                blob = bucket.blob(os.path.relpath(file_path, local_dir))
                blob.upload_from_filename(file_path)

    # Authenticate with the docker registry
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())

    # Build the Compute Engine service object
    compute_service = build("compute", "v1", credentials=creds)

    # Invalidate the cache for the specified URL map
    request_body = {
        "path": "/*",
    }
    request_id = str(uuid.uuid4())  # Generate a unique request ID

    url_map_name = backend_bucket_outputs.url_map_resource_id.split("/")[-1]
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

    if static_site.wait_for_cdn_invalidation:
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

    return service_url


# Followed these docs: https://firebase.google.com/docs/hosting/api-deploy
async def deploy_local_files_to_firebase_static_site(
    gcp_environment_config: GCPEnvironmentConfig,
    firebase_static_site: FirebaseStaticSite,
):
    try:
        import google.auth
        import google.auth.transport.requests
        from googleapiclient.discovery import build
    except ImportError:
        raise exceptions.MissingGCPDependency()

    service_url = firebase_static_site.outputs().service_url
    SITE_ID = firebase_static_site._firebase_hosting_site.resource_id

    local_dir = os.path.join(
        os.path.dirname(os.path.abspath(config.launchflow_yaml.config_path)),
        firebase_static_site.build_directory,
    )

    # Authenticate with the docker registry
    creds, _ = google.auth.default(
        quota_project_id=gcp_environment_config.project_id,  # type: ignore
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    creds.refresh(google.auth.transport.requests.Request())

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
            parent=f"sites/{SITE_ID}",
            body=request_body,
        )
        .execute()
    )

    # Extract the VERSION_ID from the response
    version_name = create_version_response.get("name")
    VERSION_ID = version_name.split("/")[-1] if version_name else None

    if not VERSION_ID:
        raise ValueError("Failed to create a new version. VERSION_ID not found.")

    pathspec = PathSpec.from_lines("gitwildmatch", firebase_static_site.build_ignore)

    # Function to determine if a file should be included based on pathspec rules
    def should_include_file(pathspec: PathSpec, file_path: str, root_dir: str):
        relative_path = os.path.relpath(file_path, root_dir)
        return not pathspec.match_file(relative_path)

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
    for root, _, files in os.walk(local_dir):
        for file in files:
            file_path = os.path.join(root, file)
            if should_include_file(pathspec, file_path, local_dir):
                file_hash, _ = gzip_and_hash_file(file_path)
                relative_path = os.path.relpath(file_path, local_dir)
                files_to_deploy[f"/{relative_path}"] = file_hash

    # Step 4: Populate files for the new version
    populate_files_request_body = {"files": files_to_deploy}

    # Make the API request to populate the files
    populate_files_response = (
        firebase_service.sites()
        .versions()
        .populateFiles(
            parent=f"sites/{SITE_ID}/versions/{VERSION_ID}",
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
                os.path.join(local_dir, file_path.lstrip("/"))
            )

            # Upload the file
            headers = {
                "Authorization": f"Bearer {creds.token}",
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
            name=f"sites/{SITE_ID}/versions/{VERSION_ID}",
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
            parent=f"sites/{SITE_ID}",
            versionName=f"sites/{SITE_ID}/versions/{VERSION_ID}",
            body=release_request_body,
        )
        .execute()
    )

    return service_url


# TODO: It looks like there might be a transient error we need to handle and retry
# Revision 'my-service-new-env-00005-zdj' is not ready and cannot serve traffic. Health check
# failed for the deployment with the user-provided VPC network. Got permission denied error.
async def release_docker_image_to_cloud_run(
    docker_image: str,
    service_manager: ServiceManager,
    gcp_environment_config: GCPEnvironmentConfig,
    cloud_run_service: CloudRunService,
    deployment_id: str,
) -> str:
    try:
        from google.cloud import run_v2
    except ImportError:
        raise exceptions.MissingGCPDependency()

    cloud_run_outputs = cloud_run_service.outputs()
    if cloud_run_outputs.gcp_id is None:
        raise exceptions.ServiceOutputsMissingField(cloud_run_service.name, "gcp_id")

    client = run_v2.ServicesAsyncClient()
    service = await client.get_service(name=cloud_run_outputs.gcp_id)
    # Updating the service container will trigger a new revision to be created
    service.template.containers[0].image = docker_image

    # Add or update the environment variables
    fields_to_add = {
        "LAUNCHFLOW_ARTIFACT_BUCKET": f"gs://{gcp_environment_config.artifact_bucket}",
        "LAUNCHFLOW_PROJECT": service_manager.project_name,
        "LAUNCHFLOW_ENVIRONMENT": service_manager.environment_name,
        "LAUNCHFLOW_CLOUD_PROVIDER": "gcp",
        "LAUNCHFLOW_DEPLOYMENT_ID": deployment_id,
    }
    for env_var in service.template.containers[0].env:
        if env_var.name in fields_to_add:
            env_var.value = fields_to_add[env_var.name]
            del fields_to_add[env_var.name]
    for key, value in fields_to_add.items():
        service.template.containers[0].env.append(run_v2.EnvVar(name=key, value=value))

    operation = await client.update_service(request=None, service=service)
    response = await operation.result()

    # This is the cloud run service url
    return response.uri


async def wait_for_op(op):
    while not op.done():
        await asyncio.sleep(2)
    return op.result()


_DISCONNECTED_RETRIES = 5


async def _retry_remote_disconnected(fn: Callable, *args, **kwargs):
    loop = asyncio.get_event_loop()
    tries = _DISCONNECTED_RETRIES
    while tries > 0:
        try:
            return await loop.run_in_executor(None, fn, *args, **kwargs)
        except ConnectionError:
            tries -= 1
            if tries == 0:
                raise
            await asyncio.sleep(2)
    raise ValueError("Failed to connect to remote service")


async def poll_mig_updating(
    client: Any, mig_name: str, project: str, region: str, timeout: timedelta
):
    def get_mig():
        return client.get(
            project=project, region=region, instance_group_manager=mig_name
        )

    mig = await _retry_remote_disconnected(get_mig)
    start_time = time.time()
    while not mig.status.is_stable:
        now = time.time()
        if now - start_time > timeout.total_seconds():
            raise exceptions.GCEServiceNotHealthyTimeout(timeout)
        await asyncio.sleep(2)
        mig = await _retry_remote_disconnected(get_mig)


async def release_docker_image_to_compute_engine(
    docker_image: str,
    service_manager: ServiceManager,
    gcp_environment_config: GCPEnvironmentConfig,
    compute_engine_service: ComputeEngineService,
    deployment_id: str,
) -> str:
    region = compute_engine_service.region or gcp_environment_config.default_region
    try:
        from google.cloud import compute
    except ImportError:
        raise exceptions.MissingGCPDependency()

    template_client = compute.InstanceTemplatesClient()
    template = compute.InstanceTemplate(
        name=f"{service_manager.service_name}-{deployment_id}",
        properties=compute.InstanceProperties(
            machine_type=compute_engine_service.machine_type,
            disks=[
                compute.AttachedDisk(
                    boot=True,
                    auto_delete=True,
                    initialize_params=compute.AttachedDiskInitializeParams(
                        disk_size_gb=compute_engine_service.disk_size_gb,
                        source_image="https://www.googleapis.com/compute/v1/projects/cos-cloud/global/images/cos-stable-109-17800-147-54",
                    ),
                ),
            ],
            tags=compute.Tags(items=[compute_engine_service._mig.resource_id]),
            labels={"container-vm": "cos-stable-109-17800-147-54"},
            metadata=compute.Metadata(
                items=[
                    compute.Items(
                        key="google-logging-enabled",
                        value="true",
                    ),
                    compute.Items(
                        key="google-monitoring-enabled",
                        value="true",
                    ),
                    compute.Items(
                        key="gce-container-declaration",
                        value=json.dumps(
                            {
                                "spec": {
                                    "containers": [
                                        {
                                            "image": docker_image,
                                            "env": [
                                                {
                                                    "name": "LAUNCHFLOW_ARTIFACT_BUCKET",
                                                    "value": f"gs://{gcp_environment_config.artifact_bucket}",
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_PROJECT",
                                                    "value": service_manager.project_name,
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_ENVIRONMENT",
                                                    "value": service_manager.environment_name,
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_CLOUD_PROVIDER",
                                                    "value": "gcp",
                                                },
                                                {
                                                    "name": "LAUNCHFLOW_DEPLOYMENT_ID",
                                                    "value": deployment_id,
                                                },
                                            ],
                                        },
                                    ]
                                },
                                "volumes": [],
                                "restartPolicy": "Always",
                            }
                        ),
                    ),
                ]
            ),
            network_interfaces=[
                compute.NetworkInterface(
                    network=f"https://www.googleapis.com/compute/beta/projects/{gcp_environment_config.project_id}/global/networks/default",
                    access_configs=[
                        compute.AccessConfig(
                            name="External NAT",
                            type="ONE_TO_ONE_NAT",
                        ),
                    ],
                )
            ],
            service_accounts=[
                compute.ServiceAccount(
                    email=gcp_environment_config.service_account_email,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
            ],
        ),
    )

    def insert_template():
        return template_client.insert(
            project=gcp_environment_config.project_id,
            instance_template_resource=template,
        )

    template_op = await _retry_remote_disconnected(insert_template)

    await wait_for_op(template_op)

    group_client = compute.RegionInstanceGroupManagersClient()

    def update_instances():
        return group_client.patch(
            instance_group_manager=compute_engine_service._mig.resource_id,
            project=gcp_environment_config.project_id,
            region=region,
            instance_group_manager_resource=compute.InstanceGroupManager(
                versions=[
                    compute.InstanceGroupManagerVersion(
                        instance_template=f"projects/{gcp_environment_config.project_id}/global/instanceTemplates/{template.name}",
                        name=template.name,
                    )
                ],
                update_policy=compute.InstanceGroupManagerUpdatePolicy(
                    type_="PROACTIVE"
                ),
            ),
        )

    update_op = await _retry_remote_disconnected(update_instances)
    await wait_for_op(update_op)
    await poll_mig_updating(
        group_client,
        compute_engine_service._mig.resource_id,
        gcp_environment_config.project_id,  # type: ignore
        region,
        compute_engine_service.deploy_timeout,
    )

    service_url = ""
    if compute_engine_service.domain:
        service_url = f"https://{compute_engine_service.domain}"

    return service_url


def _get_gke_config(cluster_id: str, cluster: "Cluster") -> Dict[str, Any]:
    try:
        from google.auth import default
        from google.auth.credentials import Credentials
        from google.auth.transport.requests import Request
    except ImportError:
        raise exceptions.MissingGCPDependency()

    results: Tuple[Credentials, Any] = default()  # type: ignore
    credentials = results[0]
    if not credentials.valid:
        credentials.refresh(Request())
    return {
        "apiVersion": "v1",
        "clusters": [
            {
                "cluster": {
                    "certificate-authority-data": cluster.master_auth.cluster_ca_certificate,
                    "server": f"https://{cluster.endpoint}",
                },
                "name": cluster_id,
            }
        ],
        "contexts": [
            {
                "context": {
                    "cluster": cluster_id,
                    "user": "gke-user",
                },
                "name": f"{cluster_id}-context",
            }
        ],
        "current-context": f"{cluster_id}-context",
        "kind": "Config",
        "preferences": {},
        "users": [
            {
                "name": "gke-user",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": credentials.token,
                            "cmd-path": "gcloud",
                            "cmd-args": "config config-helper --format=json",
                            "expiry-key": "{.credential.token_expiry}",
                            "token-key": "{.credential.access_token}",
                        },
                    }
                },
            }
        ],
    }


async def release_docker_image_to_gke(
    docker_image: str,
    service_manager: ServiceManager,
    gcp_environment_config: GCPEnvironmentConfig,
    gke_service: GKEService,
    deployment_id: str,
):
    try:
        from google.cloud import container_v1
    except ImportError:
        raise exceptions.MissingGCPDependency()
    cluster = gke_service.cluster
    location = None
    if cluster.regional:
        location = cluster.region or gcp_environment_config.default_region
    else:
        location = (
            cluster.zones[0] if cluster.zones else gcp_environment_config.default_zone
        )
    cluster_name = f"projects/{gcp_environment_config.project_id}/locations/{location}/clusters/{gke_service.cluster.resource_id}"
    gcp_client = container_v1.ClusterManagerAsyncClient()
    cluster = await gcp_client.get_cluster(name=cluster_name)
    k8_config.load_kube_config_from_dict(_get_gke_config(cluster_name, cluster))

    await update_k8s_service(
        docker_image=docker_image,
        namespace=gke_service.namespace,
        service_name=gke_service.name,
        deployment_id=deployment_id,
        launchflow_environment=service_manager.environment_name,
        launchflow_project=service_manager.project_name,
        artifact_bucket=f"gs://{gcp_environment_config.artifact_bucket}",  # type: ignore
        cloud_provider="gcp",
        k8_service_account=gcp_environment_config.service_account_email.split("@")[0],  # type: ignore
        environment_vars=gke_service.environment_variables,
    )
    # The service url doesn't change between deployment
    return gke_service.outputs().service_url


async def promote_gcp_service_image(
    gcp_service: GCPDockerService,
    from_service_state: ServiceState,
    from_gcp_environment_config: GCPEnvironmentConfig,
    to_gcp_environment_config: GCPEnvironmentConfig,
    deployment_id: str,
    promote_local: bool,
) -> Tuple[str, str]:
    service_outputs = gcp_service.outputs()

    # Step 1 - Promote the existing docker image
    if not promote_local:
        return await _promote_docker_image(
            source_env_region=from_gcp_environment_config.default_region,
            # TODO: add validation around the docker image being set
            source_docker_image=from_service_state.docker_image,  # type: ignore
            target_docker_repository=service_outputs.docker_repository,
            docker_image_name=from_service_state.name,
            docker_image_tag=deployment_id,
            target_gcp_project_id=to_gcp_environment_config.project_id,  # type: ignore
            target_artifact_bucket=to_gcp_environment_config.artifact_bucket,  # type: ignore
            target_service_account_email=to_gcp_environment_config.service_account_email,  # type: ignore
        )
    else:
        source_region = from_service_state.inputs.get("region")  # type: ignore
        if source_region is None:
            source_region = from_gcp_environment_config.default_region
        target_region = gcp_service.inputs().to_dict().get("region")
        if target_region is None:
            target_region = to_gcp_environment_config.default_region
        return await _promote_docker_image_local(
            source_service_region=source_region,
            target_service_region=target_region,
            source_docker_image=from_service_state.docker_image,  # type: ignore
            target_docker_repository=service_outputs.docker_repository,
            docker_image_name=from_service_state.name,
            docker_image_tag=deployment_id,
        )
