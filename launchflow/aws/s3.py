import dataclasses
import io
from typing import IO

from launchflow.models.enums import ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore


from typing import Union

from launchflow.aws.resource import AWSResource


@dataclasses.dataclass
class S3BucketOutputs(Outputs):
    bucket_name: str


@dataclasses.dataclass
class S3BucketInputs(ResourceInputs):
    force_destroy: bool


class S3Bucket(AWSResource[S3BucketOutputs]):
    """A storage bucket in AWS's S3 service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/s3/).

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to a S3 Bucket in your AWS account
    s3 = lf.aws.S3Bucket("my-bucket")

    # Quick utilities for reading and writing file contents
    s3.upload_from_string("file contents", "path/in/s3/file.txt")

    # You can also use the boto3 library directly
    bucket = s3.bucket()
    with open("my-file", "r") as f:
        bucket.upload_fileobj(f, "path/in/s3/file.txt")
    ```
    """

    product = ResourceProduct.AWS_S3_BUCKET.value

    def __init__(self, name: str, *, force_destroy: bool = False) -> None:
        """Create a new S3 bucket resource.

        **Args:**
        - `name (str)`: The name of the bucket. This must be globally unique.
        - `force_destroy (bool)`: If true, the bucket will be destroyed even if it contains objects.
        """
        super().__init__(
            name=name,
            # S3 buckets can only contain lowercase letters
            resource_id=name.lower(),
        )
        # public metadata
        self.force_destroy = force_destroy

    def inputs(self, environment_state: EnvironmentState) -> S3BucketInputs:
        return S3BucketInputs(
            resource_id=self.resource_id, force_destroy=self.force_destroy
        )

    def bucket(self):
        """Get the AWS bucket resource returned by the boto3 library.

        **Returns:**
        - The [AWS bucket object](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/bucket/index.html) from the boto3 library.
        """
        if boto3 is None:
            raise ImportError(
                "boto3 not found. "
                "You can install it with pip install launchflow[aws]"
            )
        connection_info = self.outputs()
        return boto3.resource("s3").Bucket(connection_info.bucket_name)

    def upload_file(self, to_upload: Union[str, IO], bucket_path: str):
        """Uploads a file to the S3 bucket.

        **Args:**
        - `to_upload (Union[str, IO])`: The file to upload. This can be a string representing the path to the file, or a file-like object.
        - `bucket_path (str)`: The path to upload the file to in the bucket.

        **Example usage:**
        ```python
        import launchflow as lf
        bucket = lf.aws.S3Bucket("my-bucket")
        bucket.upload_file("my-file.txt", "my-file.txt")
        bucket.upload_file(open("my-file.txt", "r"), "my-file.txt")
        ```
        """
        bucket = self.bucket()
        if isinstance(to_upload, str):
            bucket.upload_file(to_upload, bucket_path)
        else:
            bucket.upload_fileobj(to_upload, bucket_path)

    def upload_from_string(self, to_upload: str, bucket_path: str):
        """Uploads a string to the S3 bucket.

        **Args:**
        - `to_upload (str)`: The string to upload.
        - `bucket_path (str)`: The path to upload the string to in the bucket.

        **Example usage:**
        ```python
        import launchflow as lf

        bucket = lf.aws.S3Bucket("my-bucket")
        bucket.upload_from_string("hello", "hello.txt")
        ```
        """
        to_write = io.BytesIO(to_upload.encode("utf-8"))
        return self.upload_file(to_write, bucket_path)

    def download_file(self, bucket_path: str):
        """Downloads a file from the S3 bucket.

        **Args:**
        - `bucket_path (str)`: The path to the file in the bucket.

        **Returns:**
        - The contents of the file as bytes.

        **Example usage:**
        ```python
        import launchflow as lf
        bucket = lf.aws.S3Bucket("my-bucket")
        with open("my-file.txt", "w") as f:
            f.write(bucket.download_file("my-file.txt"))
        ```
        """
        bucket = self.bucket()
        bytes_io = io.BytesIO()
        bucket.download_fileobj(bucket_path, bytes_io)
        bytes_io.seek(0)
        return bytes_io.read()
