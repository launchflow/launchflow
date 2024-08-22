from launchflow.aws.acm import ACMCertificate
from launchflow.aws.alb import ApplicationLoadBalancer
from launchflow.aws.codebuild_project import CodeBuildProject
from launchflow.aws.ec2 import EC2
from launchflow.aws.ecr_repository import ECRRepository
from launchflow.aws.ecs_cluster import ECSCluster
from launchflow.aws.ecs_fargate import ECSFargate
from launchflow.aws.ecs_fargate_container import ECSFargateServiceContainer
from launchflow.aws.elasticache import ElasticacheRedis
from launchflow.aws.launchflow_cloud_releaser import (
    LaunchFlowCloudReleaser as AWSReleaser,
)
from launchflow.aws.rds import RDSPostgres
from launchflow.aws.s3 import S3Bucket
from launchflow.aws.secrets_manager import SecretsManagerSecret
from launchflow.aws.sqs import SQSQueue
from launchflow.docker.resource import DockerResource
from launchflow.gcp.artifact_registry_repository import ArtifactRegistryRepository
from launchflow.gcp.bigquery import BigQueryDataset
from launchflow.gcp.cloud_run import CloudRun, CloudRunServiceContainer
from launchflow.gcp.cloud_tasks import CloudTasksQueue
from launchflow.gcp.cloudsql import CloudSQLDatabase, CloudSQLPostgres, CloudSQLUser
from launchflow.gcp.compute_engine_service import ComputeEngineService
from launchflow.gcp.compute_engine import ComputeEngine
from launchflow.gcp.custom_domain_mapping import CustomDomainMapping
from launchflow.gcp.gcs import GCSBucket
from launchflow.gcp.http_health_check import HttpHealthCheck
from launchflow.gcp.launchflow_cloud_releaser import (
    LaunchFlowCloudReleaser as GCPReleaser,
)
from launchflow.gcp.memorystore import MemorystoreRedis
from launchflow.gcp.networking import FirewallAllowRule
from launchflow.gcp.pubsub import PubsubSubscription, PubsubTopic
from launchflow.gcp.regional_autoscaler import RegionalAutoscaler
from launchflow.gcp.regional_managed_instance_group import RegionalManagedInstanceGroup
from launchflow.gcp.secret_manager import SecretManagerSecret
from launchflow.gcp.workbench import WorkbenchInstance
from launchflow.models.enums import ResourceProduct, ServiceProduct
from launchflow.resource import Resource
from launchflow.service import Service

RESOURCE_PRODUCTS_TO_RESOURCES = {
    ResourceProduct.UNKNOWN.value: Resource,
    # GCP product types
    ResourceProduct.GCP_SQL_POSTGRES.value: CloudSQLPostgres,
    ResourceProduct.GCP_SQL_USER.value: CloudSQLUser,
    ResourceProduct.GCP_ARTIFACT_REGISTRY_REPOSITORY.value: ArtifactRegistryRepository,
    ResourceProduct.GCP_SQL_DATABASE.value: CloudSQLDatabase,
    ResourceProduct.GCP_PUBSUB_TOPIC.value: PubsubTopic,
    ResourceProduct.GCP_PUBSUB_SUBSCRIPTION.value: PubsubSubscription,
    ResourceProduct.GCP_STORAGE_BUCKET.value: GCSBucket,
    ResourceProduct.GCP_BIGQUERY_DATASET.value: BigQueryDataset,
    ResourceProduct.GCP_MEMORYSTORE_REDIS.value: MemorystoreRedis,
    # TODO consider having a separate resource product per compute engine type
    ResourceProduct.GCP_COMPUTE_ENGINE.value: ComputeEngine,
    ResourceProduct.GCP_SECRET_MANAGER_SECRET.value: SecretManagerSecret,
    ResourceProduct.GCP_LAUNCHFLOW_CLOUD_RELEASER.value: GCPReleaser,
    ResourceProduct.GCP_CLOUD_TASKS_QUEUE.value: CloudTasksQueue,
    ResourceProduct.GCP_CLOUD_RUN_SERVICE_CONTAINER.value: CloudRunServiceContainer,
    ResourceProduct.GCP_CUSTOM_DOMAIN_MAPPING.value: CustomDomainMapping,
    ResourceProduct.GCP_WORKBENCH_INSTANCE.value: WorkbenchInstance,
    ResourceProduct.GCP_REGIONAL_MANAGED_INSTANCE_GROUP.value: RegionalManagedInstanceGroup,
    ResourceProduct.GCP_FIREWALL_ALLOW_RULE.value: FirewallAllowRule,
    ResourceProduct.GCP_COMPUTE_HTTP_HEALTH_CHECK.value: HttpHealthCheck,
    ResourceProduct.GCP_REGIONAL_AUTO_SCALER.value: RegionalAutoscaler,
    # AWS product types
    ResourceProduct.AWS_RDS_POSTGRES.value: RDSPostgres,
    ResourceProduct.AWS_ELASTICACHE_REDIS.value: ElasticacheRedis,
    # TODO consider having a separate resource product per EC2 instance type
    ResourceProduct.AWS_EC2.value: EC2,
    ResourceProduct.AWS_ALB.value: ApplicationLoadBalancer,
    ResourceProduct.AWS_ACM_CERTIFICATE.value: ACMCertificate,
    ResourceProduct.AWS_S3_BUCKET.value: S3Bucket,
    ResourceProduct.AWS_SECRETS_MANAGER_SECRET.value: SecretsManagerSecret,
    ResourceProduct.AWS_CODEBUILD_PROJECT.value: CodeBuildProject,
    ResourceProduct.AWS_ECR_REPOSITORY.value: ECRRepository,
    ResourceProduct.AWS_ECS_FARGATE_SERVICE_CONTAINER.value: ECSFargateServiceContainer,
    ResourceProduct.AWS_ECS_CLUSTER.value: ECSCluster,
    ResourceProduct.AWS_SQS_QUEUE.value: SQSQueue,
    ResourceProduct.AWS_LAUNCHFLOW_CLOUD_RELEASER.value: AWSReleaser,
    # Local product types
    # TODO consider having a separate resource product for each local docker type
    ResourceProduct.LOCAL_DOCKER.value: DockerResource,
}


SERVICE_PRODUCTS_TO_SERVICES = {
    ServiceProduct.UNKNOWN.value: Service,
    # AWS product types
    ServiceProduct.AWS_ECS_FARGATE.value: ECSFargate,
    # GCP product types
    ServiceProduct.GCP_CLOUD_RUN.value: CloudRun,
    ServiceProduct.GCP_COMPUTE_ENGINE.value: ComputeEngineService,
}
RESOURCE_PRODUCTS_TO_RESOURCES = {
    ResourceProduct.UNKNOWN: Resource,
    # GCP product types
    ResourceProduct.GCP_SQL_POSTGRES: CloudSQLPostgres,
    ResourceProduct.GCP_SQL_USER: CloudSQLUser,
    ResourceProduct.GCP_ARTIFACT_REGISTRY_REPOSITORY: ArtifactRegistryRepository,
    ResourceProduct.GCP_SQL_DATABASE: CloudSQLDatabase,
    ResourceProduct.GCP_PUBSUB_TOPIC: PubsubTopic,
    ResourceProduct.GCP_PUBSUB_SUBSCRIPTION: PubsubSubscription,
    ResourceProduct.GCP_STORAGE_BUCKET: GCSBucket,
    ResourceProduct.GCP_BIGQUERY_DATASET: BigQueryDataset,
    ResourceProduct.GCP_MEMORYSTORE_REDIS: MemorystoreRedis,
    # TODO consider having a separate resource product per compute engine type
    ResourceProduct.GCP_COMPUTE_ENGINE: ComputeEngine,
    ResourceProduct.GCP_SECRET_MANAGER_SECRET: SecretManagerSecret,
    ResourceProduct.GCP_LAUNCHFLOW_CLOUD_RELEASER: GCPReleaser,
    ResourceProduct.GCP_CLOUD_TASKS_QUEUE: CloudTasksQueue,
    ResourceProduct.GCP_CLOUD_RUN_SERVICE_CONTAINER: CloudRunServiceContainer,
    ResourceProduct.GCP_CUSTOM_DOMAIN_MAPPING: CustomDomainMapping,
    ResourceProduct.GCP_WORKBENCH_INSTANCE: WorkbenchInstance,
    ResourceProduct.GCP_REGIONAL_MANAGED_INSTANCE_GROUP: RegionalManagedInstanceGroup,
    ResourceProduct.GCP_FIREWALL_ALLOW_RULE: FirewallAllowRule,
    ResourceProduct.GCP_COMPUTE_HTTP_HEALTH_CHECK: HttpHealthCheck,
    ResourceProduct.GCP_REGIONAL_AUTO_SCALER: RegionalAutoscaler,
    # AWS product types
    ResourceProduct.AWS_RDS_POSTGRES: RDSPostgres,
    ResourceProduct.AWS_ELASTICACHE_REDIS: ElasticacheRedis,
    # TODO consider having a separate resource product per EC2 instance type
    ResourceProduct.AWS_EC2: EC2,
    ResourceProduct.AWS_ALB: ApplicationLoadBalancer,
    ResourceProduct.AWS_ACM_CERTIFICATE: ACMCertificate,
    ResourceProduct.AWS_S3_BUCKET: S3Bucket,
    ResourceProduct.AWS_SECRETS_MANAGER_SECRET: SecretsManagerSecret,
    ResourceProduct.AWS_CODEBUILD_PROJECT: CodeBuildProject,
    ResourceProduct.AWS_ECR_REPOSITORY: ECRRepository,
    ResourceProduct.AWS_ECS_FARGATE_SERVICE_CONTAINER: ECSFargateServiceContainer,
    ResourceProduct.AWS_ECS_CLUSTER: ECSCluster,
    ResourceProduct.AWS_SQS_QUEUE: SQSQueue,
    ResourceProduct.AWS_LAUNCHFLOW_CLOUD_RELEASER: AWSReleaser,
    # Local product types
    # TODO consider having a separate resource product for each local docker type
    ResourceProduct.LOCAL_DOCKER: DockerResource,
}


SERVICE_PRODUCTS_TO_SERVICES = {
    ServiceProduct.UNKNOWN: Service,
    # AWS product types
    ServiceProduct.AWS_ECS_FARGATE: ECSFargate,
    # GCP product types
    ServiceProduct.GCP_CLOUD_RUN: CloudRun,
    ServiceProduct.GCP_COMPUTE_ENGINE: ComputeEngineService,
}
