from enum import Enum


class CloudProvider(str, Enum):
    UNKNOWN = "unknown"
    GCP = "gcp"
    AWS = "aws"


class ResourceProduct(str, Enum):
    UNKNOWN = "unknown"
    # GCP product types
    GCP_SQL_POSTGRES = "gcp_sql_postgres"
    GCP_SQL_USER = "gcp_sql_user"
    GCP_ARTIFACT_REGISTRY_REPOSITORY = "gcp_artifact_registry_repository"
    GCP_SQL_DATABASE = "gcp_sql_database"
    GCP_PUBSUB_TOPIC = "gcp_pubsub_topic"
    GCP_PUBSUB_SUBSCRIPTION = "gcp_pubsub_subscription"
    GCP_STORAGE_BUCKET = "gcp_storage_bucket"
    GCP_BACKEND_BUCKET = "gcp_backend_bucket"
    GCP_BIGQUERY_DATASET = "gcp_bigquery_dataset"
    GCP_MEMORYSTORE_REDIS = "gcp_memorystore_redis"
    GCP_COMPUTE_ENGINE = "gcp_compute_engine"
    GCP_SECRET_MANAGER_SECRET = "gcp_secret_manager_secret"
    GCP_LAUNCHFLOW_CLOUD_RELEASER = "gcp_launchflow_cloud_releaser"
    GCP_CLOUD_TASKS_QUEUE = "gcp_cloud_tasks_queue"
    GCP_CLOUD_RUN_SERVICE_CONTAINER = "gcp_cloud_run_service_container"
    GCP_REGIONAL_MANAGED_INSTANCE_GROUP = "gcp_regional_managed_instance_group"
    GCP_CUSTOM_DOMAIN_MAPPING = "gcp_custom_domain_mapping"
    GCP_WORKBENCH_INSTANCE = "gcp_workbench_instance"
    GCP_FIREWALL_ALLOW_RULE = "gcp_firewall_allow_rule"
    GCP_COMPUTE_HTTP_HEALTH_CHECK = "gcp_compute_http_health_check"
    GCP_REGIONAL_AUTOSCALER = "gcp_regional_autoscaler"
    GCP_GKE_CLUSTER = "gcp_gke_cluster"
    GCP_GKE_NODE_POOL = "gcp_gke_node_pool"
    GCP_FIREBASE_PROJECT = "gcp_firebase_project"
    GCP_FIREBASE_HOSTING_SITE = "gcp_firebase_hosting_site"
    GCP_GLOBAL_IP_ADDRESS = "gcp_global_ip_address"
    GCP_MANAGED_SSL_CERTIFICATE = "gcp_managed_ssl_certificate"
    GCP_GKE_CUSTOM_DOMAIN_MAPPING = "gcp_gke_custom_domain_mapping"
    # AWS product types
    AWS_RDS_POSTGRES = "aws_rds_postgres"
    AWS_RDS = "aws_rds"
    AWS_ELASTICACHE_REDIS = "aws_elasticache_redis"
    AWS_EC2 = "aws_ec2"
    AWS_S3_BUCKET = "aws_s3_bucket"
    AWS_SECRETS_MANAGER_SECRET = "aws_secrets_manager_secret"
    AWS_CODEBUILD_PROJECT = "aws_codebuild_project"
    AWS_ECR_REPOSITORY = "aws_ecr_repository"
    AWS_ECS_FARGATE_SERVICE_CONTAINER = "aws_ecs_fargate_service_container"
    AWS_LAMBDA_FUNCTION = "aws_lambda_function"
    AWS_LAMBDA_FUNCTION_URL = "aws_lambda_function_url"
    AWS_NAT_GATEWAY = "aws_nat_gateway"
    AWS_ELASTIC_IP = "aws_elastic_ip"
    AWS_API_GATEWAY = "aws_api_gateway"
    AWS_API_GATEWAY_LAMBDA_INTEGRATION = "aws_api_gateway_lambda_integration"
    AWS_API_GATEWAY_ROUTE = "aws_api_gateway_route"
    AWS_LAMBDA_EVENT_MAPPING = "aws_lambda_event_mapping"
    AWS_ECS_CLUSTER = "aws_ecs_cluster"
    AWS_ALB = "aws_application_load_balancer"
    AWS_ACM_CERTIFICATE = "aws_acm_certificate"
    AWS_SQS_QUEUE = "aws_sqs_queue"
    AWS_LAUNCHFLOW_CLOUD_RELEASER = "aws_launchflow_cloud_releaser"
    # Local product types
    LOCAL_DOCKER = "local_docker"
    # Kubernetes product types
    KUBERNETES_SERVICE_CONTAINER = "kubernetes_service_container"
    KUBERNETES_HORIZONTAL_POD_AUTOSCALER = "kubernetes_horizontal_pod_autoscaler"


class ServiceProduct(str, Enum):
    UNKNOWN = "unknown"
    # GCP product types
    GCP_STATIC_SITE = "gcp_static_site"
    GCP_FIREBASE_STATIC_SITE = "gcp_firebase_static_site"
    GCP_CLOUD_RUN = "gcp_cloud_run"
    GCP_COMPUTE_ENGINE = "gcp_compute_engine"
    GCP_GKE = "gcp_gke"
    # AWS product types
    AWS_ECS_FARGATE = "aws_ecs_fargate"
    AWS_LAMBDA = "aws_lambda"


class EnvironmentType(str, Enum):
    UNKNOWN = "unknown"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class EnvironmentStatus(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    CREATE_FAILED = "create_failed"
    DELETE_FAILED = "delete_failed"
    CREATING = "creating"
    DELETING = "deleting"

    def is_pending(self):
        return self in [EnvironmentStatus.CREATING, EnvironmentStatus.DELETING]


class ResourceStatus(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    CREATE_FAILED = "create_failed"
    DELETE_FAILED = "delete_failed"
    UPDATE_FAILED = "update_failed"
    REPLACE_FAILED = "replace_failed"
    CREATING = "creating"
    DESTROYING = "destroying"
    UPDATING = "updating"
    REPLACING = "replacing"

    def is_pending(self):
        return self in [
            ResourceStatus.CREATING,
            ResourceStatus.DESTROYING,
            ResourceStatus.UPDATING,
            ResourceStatus.REPLACING,
        ]


class ServiceStatus(str, Enum):
    UNKNOWN = "unknown"
    READY = "ready"
    DEPLOY_FAILED = "deploy_failed"
    DELETE_FAILED = "delete_failed"
    PROMOTE_FAILED = "promote_failed"
    CREATE_FAILED = "create_failed"
    UPDATE_FAILED = "update_failed"
    DEPLOYING = "deploying"
    DESTROYING = "destroying"
    PROMOTING = "promoting"
    CREATING = "creating"
    UPDATING = "updating"

    def is_pending(self):
        return self in [
            ServiceStatus.DEPLOYING,
            ServiceStatus.DESTROYING,
            ServiceStatus.PROMOTING,
            ServiceStatus.CREATING,
            ServiceStatus.UPDATING,
        ]
