import asyncio
import gzip
import hashlib
import io
import os
import uuid
from typing import IO, List

import requests
from docker.errors import APIError, BuildError
from pathspec import PathSpec

from launchflow import exceptions
from launchflow.config import config
from launchflow.gcp.firebase_site import FirebaseStaticSite
from launchflow.gcp.static_site import GCSWebsite
from launchflow.models.flow_state import GCPEnvironmentConfig
from launchflow.workflows.utils import tar_source_in_memory


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
    build_log_file: IO,
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
    build_url = f"https://console.cloud.google.com/cloud-build/builds/{operation.metadata.build.id}?project={gcp_project_id}"  # type: ignore
    # Add logs to the table to the table
    try:
        # For some reason timeout=None is not working, so we set it to 1 hour
        build_log_file.write(
            f"Building image {tagged_image_name}\nSee remote build logs at: {build_url}\n"
        )
        await operation.result(timeout=3600)
        build_log_file.write(f"Successfully built image {tagged_image_name}\n")
    except Exception as e:
        build_log_file.write(
            f"Error running GCP Cloud Build: {e}\nSee remote build logs at: {build_url}\n"
        )
        raise e

    # Return the docker image name
    return tagged_image_name


def _write_build_logs(f: IO, log_stream):
    for chunk in log_stream:
        if "stream" in chunk:
            f.write(chunk["stream"])
        if "status" in chunk:
            f.write(chunk["status"] + "\n")


async def _promote_docker_image(
    source_env_region: str,
    source_docker_image: str,
    target_docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    target_gcp_project_id: str,
    target_artifact_bucket: str,
    target_service_account_email: str,
    build_log_file: IO,
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
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore

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
                        f"echo {creds.token} | docker login --username=oauth2accesstoken --password-stdin https://{source_env_region}-docker.pkg.dev "  # type: ignore
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
    build_url = f"https://console.cloud.google.com/cloud-build/builds/{operation.metadata.build.id}?project={target_gcp_project_id}"  # type: ignore
    try:
        # For some reason timeout=None is not working, so we set it to 1 hour
        build_log_file.write(
            f"Promoting image to {tagged_target_image}\nSee remote build logs at: {build_url}\n"
        )
        await operation.result(timeout=3600)
        build_log_file.write(f"Successfully promoted image to {tagged_target_image}\n")
    except Exception as e:
        build_log_file.write(
            f"Error running GCP Cloud Build: {e}\nSee remote build logs at: {build_url}\n"
        )
        raise e

    # Return the docker image name
    return tagged_target_image


async def _promote_docker_image_local(
    source_artifact_registry_repository: str,
    target_artifact_registry_repository: str,
    source_docker_image: str,
    docker_image_name: str,
    docker_image_tag: str,
    build_log_file: IO,
):
    target_image = f"{target_artifact_registry_repository}/{docker_image_name}"
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
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore
    if source_token is None:
        source_token = creds.token  # type: ignore

    def promote_image():
        source_registry_name = source_artifact_registry_repository.split("/")[0]
        docker_client = from_env()
        docker_client.login(
            username="oauth2accesstoken",
            password=source_token,
            registry=f"https://{source_registry_name}",
        )
        try:
            image = docker_client.images.pull(source_docker_image)
        except APIError:
            sa_email = None
            if hasattr(creds, "service_account_email"):
                sa_email = creds.service_account_email  # type: ignore
            raise exceptions.GCPDockerPullFailed(
                service_account_email=sa_email, docker_image=source_docker_image
            )
        image.tag(target_image, docker_image_tag)
        image.tag(target_image, "latest")
        output = docker_client.images.push(
            target_image, docker_image_tag, stream=True, decode=True
        )
        _write_build_logs(build_log_file, output)
        output = docker_client.images.push(
            target_image, "latest", stream=True, decode=True
        )
        _write_build_logs(build_log_file, output)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, promote_image)
    # Return the docker image name
    return tagged_target_image


# TODO: Look into cleaning up old images. I noticed my docker images were taking up a lot of space
# after running this workflow multiple times
async def _build_docker_image_local(
    docker_repository: str,
    docker_image_name: str,
    docker_image_tag: str,
    local_source_dir: str,
    dockerfile_path: str,
    build_log_file: IO,
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
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore
    docker_client.login(
        username="oauth2accesstoken",
        password=creds.token,  # type: ignore
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
                path=local_source_dir,
                dockerfile=dockerfile_path,
                tag=tagged_image_name,
                cache_from=cache_from,
                # NOTE: this is required to build on mac
                platform="linux/amd64",
            ),
        )
        _write_build_logs(build_log_file, log_stream)
    except BuildError as e:
        _write_build_logs(build_log_file, e.build_log)
        raise e

    # Tag as latest
    docker_client.images.get(tagged_image_name).tag(latest_image_name)

    # Push the images to the registry
    docker_client.images.push(tagged_image_name)
    docker_client.images.push(latest_image_name)

    # Return the docker image name
    return tagged_image_name


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
    creds.refresh(google.auth.transport.requests.Request())  # type: ignore

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


async def build_artifact_registry_docker_image(
    dockerfile_path: str,
    build_directory: str,
    build_ignore: List[str],
    build_log_file: IO,
    artifact_registry_repository: str,
    launchflow_project_name: str,
    launchflow_environment_name: str,
    launchflow_service_name: str,
    launchflow_deployment_id: str,
    gcp_environment_config: GCPEnvironmentConfig,
    build_local: bool,
) -> str:
    if build_local:
        del (
            build_ignore
        )  # TODO: Use this to ignore files while building the docker image

        docker_image = await _build_docker_image_local(
            docker_repository=artifact_registry_repository,
            docker_image_name=launchflow_service_name,
            docker_image_tag=launchflow_deployment_id,
            local_source_dir=build_directory,
            dockerfile_path=dockerfile_path,
            build_log_file=build_log_file,
        )
    else:
        source_tarball_gcs_path = f"builds/{launchflow_project_name}/{launchflow_environment_name}/services/{launchflow_service_name}/source.tar.gz"
        # Step 1 - Upload the source tarball to GCS
        await _upload_source_tarball_to_gcs(
            source_tarball_gcs_path=source_tarball_gcs_path,
            artifact_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
            local_source_dir=build_directory,
            build_ignore=build_ignore,
        )

        # Step 2 - Build and push the docker image
        return await _run_docker_gcp_cloud_build(
            docker_repository=artifact_registry_repository,
            docker_image_name=launchflow_service_name,
            docker_image_tag=launchflow_deployment_id,
            gcs_source_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
            gcs_source_object=source_tarball_gcs_path,
            gcp_project_id=gcp_environment_config.project_id,  # type: ignore
            dockerfile_path=dockerfile_path,
            artifact_bucket=gcp_environment_config.artifact_bucket,  # type: ignore
            service_account_email=gcp_environment_config.service_account_email,  # type: ignore
            build_log_file=build_log_file,
        )

    return docker_image


async def promote_artifact_registry_docker_image(
    build_log_file: IO,
    from_artifact_registry_repository: str,
    to_artifact_registry_repository: str,
    launchflow_service_name: str,
    from_launchflow_deployment_id: str,
    to_launchflow_deployment_id: str,
    from_gcp_environment_config: GCPEnvironmentConfig,
    to_gcp_environment_config: GCPEnvironmentConfig,
    promote_local: bool,
) -> str:
    if promote_local:
        return await _promote_docker_image_local(
            source_artifact_registry_repository=from_artifact_registry_repository,
            target_artifact_registry_repository=to_artifact_registry_repository,
            source_docker_image=f"{from_artifact_registry_repository}/{launchflow_service_name}:{from_launchflow_deployment_id}",
            docker_image_name=launchflow_service_name,
            docker_image_tag=to_launchflow_deployment_id,
            build_log_file=build_log_file,
        )
    else:
        return await _promote_docker_image(
            source_env_region=from_gcp_environment_config.default_region,
            # TODO: add validation around the docker image being set
            source_docker_image=f"{from_artifact_registry_repository}/{launchflow_service_name}:{from_launchflow_deployment_id}",
            target_docker_repository=to_artifact_registry_repository,
            docker_image_name=launchflow_service_name,
            docker_image_tag=to_launchflow_deployment_id,
            target_gcp_project_id=to_gcp_environment_config.project_id,  # type: ignore
            target_artifact_bucket=to_gcp_environment_config.artifact_bucket,  # type: ignore
            target_service_account_email=to_gcp_environment_config.service_account_email,  # type: ignore
            build_log_file=build_log_file,
        )
