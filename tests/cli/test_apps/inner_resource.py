# ruff: noqa
import launchflow


def inner():
    # Should be ignored because it's not a top-level resource
    inner_fn_bucket = launchflow.gcp.GCSBucket("inner-bucket")


class InnerClass:
    # Should be ignored because it's not a top-level resource
    inner_class_bucket = launchflow.gcp.GCSBucket("inner-class-bucket")


bucket = launchflow.gcp.GCSBucket("bucket")
