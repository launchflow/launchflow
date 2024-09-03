import dataclasses
import io
from typing import IO, Dict, Optional

from launchflow.gcp_clients import get_storage_client
from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState

try:
    from google.cloud import storage  # type: ignore
except ImportError:
    storage = None  # type: ignore


from typing import Union

from launchflow.gcp.resource import GCPResource
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class GCSBucketOutputs(Outputs):
    bucket_name: str


@dataclasses.dataclass
class BucketInputs(ResourceInputs):
    location: str
    force_destroy: bool
    uniform_bucket_level_access: bool


class GCSBucket(GCPResource[GCSBucketOutputs]):
    """A storage bucket in Google Cloud Storage.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/storage/docs/overview).

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to a GCS Bucket in your GCP project
    gcs = lf.gcp.GCSBucket("my-bucket")

    # Quick utilities for reading and writing file contents
    gcs.upload_from_string("file contents", "path/in/gcs/file.txt")

    # You can also use the google-cloud-storage library directly
    bucket = gcs.bucket()
    bucket.blob("my-file").upload_from_filename("my-file")
    ```
    """

    product = ResourceProduct.GCP_STORAGE_BUCKET.value

    def __init__(
        self,
        name: str,
        *,
        location: str = "US",
        force_destroy: bool = False,
        uniform_bucket_level_access: bool = False,
    ) -> None:
        """Create a new GCS Bucket resource.

        **Args:**
        - `name (str)`: The name of the bucket. This must be globally unique.
        - `location (str)`: The location of the bucket. Defaults to "US".
        - `force_destroy (bool)`: If true, the bucket will be destroyed even if it's not empty. Defaults to False.
        - `uniform_bucket_level_access (bool)`: If true, enables uniform bucket-level access for the bucket. Defaults to False.
        """
        super().__init__(
            name=name,
            replacement_arguments={"location"},
            # GCS buckets can only contain lowercase letters
            resource_id=name.lower(),
        )
        # public metadata
        self.location = location
        self.force_destroy = force_destroy
        self.uniform_bucket_level_access = uniform_bucket_level_access

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        return {"google_storage_bucket.bucket": self.resource_id}

    def inputs(self, environment_state: EnvironmentState) -> BucketInputs:
        return BucketInputs(
            resource_id=self.resource_id,
            location=self.location,
            force_destroy=self.force_destroy,
            uniform_bucket_level_access=self.uniform_bucket_level_access,
        )

    def bucket(self):
        """Get the GCS bucket object returned by the google-cloud-storage library.

        **Returns:**
        - The [GCS bucket object](https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.bucket.Bucket) from the GCS client library.
        """
        if storage is None:
            raise ImportError(
                "google-cloud-storage not found. "
                "You can install it with pip install launchflow[gcp]"
            )
        connection_info = self.outputs()
        # TODO: Add project_id to connection_info and pass it to the client.
        # Once this is added, add a client() method to GCPResource that returns the
        # client setup with the project_id
        return get_storage_client().get_bucket(connection_info.bucket_name)

    def upload_file(self, to_upload: Union[str, IO], bucket_path: str) -> None:
        """Uploads a file to the GCS bucket.

        **Args:**
        - `to_upload (Union[str, IO])`: The file to upload. This can be a string representing the path to the file, or a file-like object.
        - `bucket_path (str)`: The path to upload the file to in the bucket.

        **Example usage:**

        ```python
        import launchflow as lf

        bucket = lf.gcp.GCSBucket("my-bucket")
        bucket.upload_file("my-file.txt", "my-file.txt")
        bucket.upload_file(open("my-file.txt", "r"), "my-file.txt")
        ```
        """
        bucket = self.bucket()
        if isinstance(to_upload, str):
            bucket.blob(bucket_path).upload_from_filename(to_upload)
        else:
            bucket.blob(bucket_path).upload_from_file(to_upload)

    def upload_from_string(self, to_upload: str, bucket_path: str) -> None:
        """Uploads a string to the GCS bucket.

        **Args:**
        - `to_upload (str)`: The string to upload.
        - `bucket_path (str)`: The path to upload the string to in the bucket.

        **Example usage:**
        ```python
        import launchflow as lf

        bucket = lf.gcp.GCSBucket("my-bucket")
        bucket.upload_from_string("hello", "hello.txt")
        ```
        """
        to_write = io.BytesIO(to_upload.encode("utf-8"))
        self.upload_file(to_write, bucket_path)

    def download_file(self, bucket_path: str) -> bytes:
        """Downloads a file from the GCS bucket.

        **Args:**
        - `bucket_path (str)`: The path to the file in the bucket.

        **Returns:**
        - The contents of the file as a bytes object.

        **Example usage:**
        ```python
        import launchflow as lf

        bucket = lf.gcp.GCSBucket("my-bucket")
        with open("my-file.txt", "w") as f:
            f.write(bucket.download_file("my-file.txt"))
        ```
        """
        bucket = self.bucket()
        return bucket.blob(bucket_path).download_as_bytes()


@dataclasses.dataclass
class BackendBucketOutputs(Outputs):
    bucket_name: str
    cdn_ip_address: str
    url_map_resource_id: str


@dataclasses.dataclass
class BackendBucketInputs(ResourceInputs):
    location: str
    force_destroy: bool
    custom_domain: Optional[str]
    main_page_suffix: str
    not_found_page: str


class BackendBucket(GCPResource[BackendBucketOutputs]):
    product = ResourceProduct.GCP_BACKEND_BUCKET.value

    def __init__(
        self,
        name: str,
        *,
        location: str = "US",
        force_destroy: bool = False,
        custom_domain: Optional[str] = None,
        main_page_suffix: str = "index.html",
        not_found_page: str = "404.html",
    ) -> None:
        """Create a new GCS Backend Bucket resource.
        **Args:**
        - `name (str)`: The name of the bucket. This must be globally unique.
        - `location (str)`: The location of the bucket. Defaults to "US".
        - `force_destroy (bool)`: If true, the bucket will be destroyed even if it's not empty. Defaults to False.
        - `custom_domain (Optional[str])`: A custom domain to map to the bucket
        """
        super().__init__(
            name=name,
            replacement_arguments={"location"},
            # GCS buckets can only contain lowercase letters
            resource_id=name.lower(),
        )
        # public metadata
        self.location = location
        self.force_destroy = force_destroy
        self.custom_domain = custom_domain
        self.main_page_suffix = main_page_suffix
        self.not_found_page = not_found_page

    def inputs(self, environment_state: EnvironmentState) -> BackendBucketInputs:
        return BackendBucketInputs(
            resource_id=self.resource_id,
            location=self.location,
            force_destroy=self.force_destroy,
            custom_domain=self.custom_domain,
            main_page_suffix=self.main_page_suffix,
            not_found_page=self.not_found_page,
        )
