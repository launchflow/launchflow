import launchflow

# Resources in this directory should be ignored
bucket = launchflow.gcp.GCSBucket("bucket")

# Services in this directory should be ignored
service = launchflow.gcp.CloudRunService("service")
