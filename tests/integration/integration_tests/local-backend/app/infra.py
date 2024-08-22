import launchflow as lf
from launchflow.managers.environment_manager import EnvironmentManager

environment_manager = EnvironmentManager(
    project_name=lf.project,
    environment_name=lf.environment,
    backend=lf.lf_config.launchflow_yaml.backend,
)
environment = environment_manager.load_environment_sync()

if environment.gcp_config is not None:
    bucket = lf.gcp.GCSBucket(f"{lf.project}-{lf.environment}-gcs-bucket")
    run_service = lf.gcp.CloudRun("fastapi-service", dockerfile="Dockerfile.gcp")
    gce_service = lf.gcp.compute_engine_service.ComputeEngineService(
        "gce-service", dockerfile="Dockerfile.gcp", port=8080
    )
elif environment.aws_config is not None:
    bucket = lf.aws.S3Bucket(
        f"{lf.project}-{lf.environment}-s3-bucket", force_destroy=True
    )
    run_service = lf.aws.ECSFargate(
        "fastapi-service", dockerfile="Dockerfile.aws", port=8080
    )
else:
    raise AssertionError("Environment wasn't set up properly")
