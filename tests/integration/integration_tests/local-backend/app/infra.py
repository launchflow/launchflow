import launchflow as lf
from launchflow.managers.environment_manager import EnvironmentManager

environment_manager = EnvironmentManager(
    project_name=lf.project,
    environment_name=lf.environment,
    backend=lf.lf_config.launchflow_yaml.backend,
)
environment = environment_manager.load_environment_sync()

run_service = None

if environment.gcp_config is not None:
    bucket = lf.gcp.GCSBucket(f"{lf.project}-{lf.environment}-gcs-bucket")
    run_service = lf.gcp.CloudRun(
        "fastapi-service",
        dockerfile="Dockerfile.gcp",
        domain="cr.launchflow.app",
    )
    gce_service = lf.gcp.compute_engine_service.ComputeEngineService(
        "gce-service",
        dockerfile="Dockerfile.gcp",
        port=8080,
        domain="gce.launchflow.app",
    )
    cluster = lf.gcp.GKECluster("cluster")
    k8_service = lf.gcp.GKEService(
        "k8-service", dockerfile="Dockerfile.gcp", container_port=8080, cluster=cluster
    )
elif environment.aws_config is not None:
    bucket = lf.aws.S3Bucket(f"{lf.project}-{lf.environment}-s3-bucket")
    run_service = lf.aws.ECSFargate(
        "fastapi-service", dockerfile="Dockerfile.aws", port=8080, desired_count=2
    )
else:
    raise AssertionError("Environment wasn't set up properly")
