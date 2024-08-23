from launchflow import exceptions
from launchflow.gcp_clients import get_storage_client
from launchflow.models.enums import CloudProvider, ResourceProduct
from launchflow.workflows.commands.tf_commands import TFDestroyCommand
from launchflow.workflows.destroy_resource_tofu.schemas import DestroyResourceTofuInputs
from launchflow.workflows.utils import run_tofu


async def delete_tofu_resource(inputs: DestroyResourceTofuInputs):
    state_prefix = inputs.launchflow_uri.tf_state_prefix(module=inputs.resource.product)

    tf_vars = {}
    is_k8_resource = (
        inputs.resource.product == ResourceProduct.KUBERNETES_SERVICE_CONTAINER
    )
    if is_k8_resource:
        k8_inputs = inputs.resource.inputs
        if k8_inputs is None:
            # if there was no inputs there is nothing to do
            return
        # tf_vars["cluster_id"] = k8_inputs["cluster_id"]
        tf_vars["cluster_id"] = (
            "projects/caleb-hello-world-dev-3204/locations/us-central1-a/clusters/my-cluster"
        )
        tf_vars["k8_provider"] = k8_inputs["k8_provider"]
        module_dir = "empty/kubernetes_empty"

    elif (
        inputs.resource.cloud_provider == CloudProvider.GCP
        and inputs.gcp_env_config is not None
    ):
        tf_vars["gcp_project_id"] = inputs.gcp_env_config.project_id
        module_dir = "empty/gcp_empty"
    elif (
        inputs.resource.cloud_provider == CloudProvider.AWS
        and inputs.aws_env_config is not None
    ):
        tf_vars["aws_region"] = inputs.aws_env_config.region  # type: ignore
        module_dir = "empty/aws_empty"
    else:
        # TODO: validate that this is correct
        return

    tf_apply_command = TFDestroyCommand(
        tf_module_dir=module_dir,
        backend=inputs.backend,
        tf_state_prefix=state_prefix,
        tf_vars=tf_vars,
        logs_file=inputs.logs_file,
        launchflow_state_url=inputs.launchflow_uri.launchflow_tofu_state_url(
            inputs.lock_id, module=inputs.resource.product
        ),
    )

    await run_tofu(tf_apply_command)

    output_key = f"resources/{inputs.launchflow_uri.resource_name}.yaml"
    if inputs.gcp_env_config is not None:
        try:
            from google.api_core.exceptions import NotFound
        except ImportError:
            raise exceptions.MissingGCPDependency()
        try:
            client = get_storage_client()
            remote_bucket = client.bucket(inputs.gcp_env_config.artifact_bucket)
            remote_bucket.blob(output_key).delete()
        except NotFound:
            pass
    if inputs.aws_env_config is not None:
        try:
            import boto3
        except ImportError:
            raise exceptions.MissingAWSDependency()
        client = boto3.client("s3")
        client.delete_object(
            Bucket=inputs.aws_env_config.artifact_bucket,
            Key=output_key,
        )
    return
