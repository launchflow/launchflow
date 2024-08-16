from launchflow.gcp import GCSBucket as CustomBucketName
from launchflow.gcp.gcs import GCSBucket

bucket = GCSBucket("bucket")
custom_bucket = CustomBucketName("custom_bucket")
