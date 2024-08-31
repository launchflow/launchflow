## GCSBucket

A storage bucket in Google Cloud Storage.

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

### initialization

Create a new GCS Bucket resource.

**Args:**
- `name (str)`: The name of the bucket. This must be globally unique.
- `location (str)`: The location of the bucket. Defaults to "US".
- `force_destroy (bool)`: If true, the bucket will be destroyed even if it's not empty. Defaults to False.
- `uniform_bucket_level_access (bool)`: If true, enables uniform bucket-level access for the bucket. Defaults to False.

### bucket

```python
GCSBucket.bucket()
```

Get the GCS bucket object returned by the google-cloud-storage library.

**Returns:**
- The [GCS bucket object](https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.bucket.Bucket) from the GCS client library.

### upload\_file

```python
GCSBucket.upload_file(to_upload: Union[str, IO], bucket_path: str) -> None
```

Uploads a file to the GCS bucket.

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

### upload\_from\_string

```python
GCSBucket.upload_from_string(to_upload: str, bucket_path: str) -> None
```

Uploads a string to the GCS bucket.

**Args:**
- `to_upload (str)`: The string to upload.
- `bucket_path (str)`: The path to upload the string to in the bucket.

**Example usage:**
```python
import launchflow as lf

bucket = lf.gcp.GCSBucket("my-bucket")
bucket.upload_from_string("hello", "hello.txt")
```

### download\_file

```python
GCSBucket.download_file(bucket_path: str) -> bytes
```

Downloads a file from the GCS bucket.

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

## BackendBucket

### initialization

Create a new GCS Backend Bucket resource.
**Args:**
- `name (str)`: The name of the bucket. This must be globally unique.
- `location (str)`: The location of the bucket. Defaults to "US".
- `force_destroy (bool)`: If true, the bucket will be destroyed even if it's not empty. Defaults to False.
- `custom_domain (Optional[str])`: A custom domain to map to the bucket
