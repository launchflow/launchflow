import os
from typing import Union

from launchflow import exceptions
from launchflow.gcp_clients import (
    delete_file_from_gcs_sync,
    read_from_gcs_sync,
    write_to_gcs_sync,
)


def _get_boto_client():
    try:
        import boto3
    except ImportError:
        raise exceptions.MissingAWSDependency()
    return boto3.client("s3")


def read_file(file_path: str) -> str:
    if file_path.startswith("s3://"):
        # Read from S3
        s3_client = _get_boto_client()
        file_path = file_path.replace("s3://", "")
        bucket, key = file_path.split("/", 1)
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    elif file_path.startswith("gs://"):
        # Read from GCS
        file_path = file_path.replace("gs://", "")
        bucket, prefix = file_path.split("/", 1)
        return read_from_gcs_sync(bucket, prefix)
    else:
        with open(file_path, "r") as f:
            return f.read()


def write_file(file_path: str, content: Union[str, bytes]):
    if file_path.startswith("s3://"):
        # Write to S3
        s3_client = _get_boto_client()
        file_path = file_path.replace("s3://", "")
        bucket, key = file_path.split("/", 1)
        s3_client.put_object(Bucket=bucket, Key=key, Body=content)
    elif file_path.startswith("gs://"):
        # Write to GCS
        file_path = file_path.replace("gs://", "")
        bucket, prefix = file_path.split("/", 1)
        write_to_gcs_sync(bucket, prefix, content)  # type: ignore
    else:
        with open(file_path, "w") as f:
            f.write(content)  # type: ignore


def delete_file(file_path: str):
    if file_path.startswith("s3://"):
        # Delete from S3
        s3_client = _get_boto_client()
        file_path = file_path.replace("s3://", "")
        bucket, key = file_path.split("/", 1)
        s3_client.delete_object(Bucket=bucket, Key=key)
    elif file_path.startswith("gs://"):
        # Delete from GCS
        file_path = file_path.replace("gs://", "")
        bucket, prefix = file_path.split("/", 1)
        delete_file_from_gcs_sync(bucket, prefix)
    else:
        os.remove(file_path)
