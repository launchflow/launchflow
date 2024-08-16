---
title: Dynamic Resource Names
nextjs:
  metadata:
    title: Dynamic Resource Names
    description: Learn how to use project and environment names in LaunchFlow to create dynamic resource names.
---

Sometimes you'll want to give your resources a name that is specific to the project or environment that they are in. This is especially useful for resources that require globally unique names such as GCS and S3 buckets. To do this you can use the `project` and `environment` attributes of the `launchflow` module.

```python
import launchflow as lf

gcs_bucket = lf.gcp.GCSBucket(
    name=f"my-bucket-{lf.project}-{lf.environment}"
)
s3_bucket = lf.aws.S3Bucket(
    name=f"my-bucket-{lf.project}-{lf.environment}"
)
```

Now when you run `lf create --project=my-project --environment=dev` the name of the bucket will be `my-bucket-my-project-dev`. This will also work for any of our other commands that parse resources from your code such as `destroy` and `clean`.
