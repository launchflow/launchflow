## S3Bucket

A storage bucket in AWS's S3 service.

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

### initialization

Create a new S3 bucket resource.

**Args:**
- `name (str)`: The name of the bucket. This must be globally unique.
- `force_destroy (bool)`: If true, the bucket will be destroyed even if it contains objects.

### bucket

```python
S3Bucket.bucket()
```

Get the AWS bucket resource returned by the boto3 library.

**Returns:**
- The [AWS bucket object](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/bucket/index.html) from the boto3 library.

### upload\_file

```python
S3Bucket.upload_file(to_upload: Union[str, IO], bucket_path: str)
```

Uploads a file to the S3 bucket.

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

### upload\_from\_string

```python
S3Bucket.upload_from_string(to_upload: str, bucket_path: str)
```

Uploads a string to the S3 bucket.

**Args:**
- `to_upload (str)`: The string to upload.
- `bucket_path (str)`: The path to upload the string to in the bucket.

**Example usage:**
```python
import launchflow as lf

bucket = lf.aws.S3Bucket("my-bucket")
bucket.upload_from_string("hello", "hello.txt")
```

### download\_file

```python
S3Bucket.download_file(bucket_path: str)
```

Downloads a file from the S3 bucket.

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
