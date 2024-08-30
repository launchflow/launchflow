import datetime
import sys
from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple, Type

from launchflow import Resource
from launchflow.aws.elasticache import ElasticacheRedis
from launchflow.aws.rds import RDS
from launchflow.aws.s3 import S3Bucket
from launchflow.cli.gen.template import ProjectGenerator
from launchflow.gcp.cloudsql import CloudSQLPostgres
from launchflow.gcp.compute_engine import ComputeEngineRedis
from launchflow.gcp.gcs import GCSBucket
from launchflow.gcp.memorystore import MemorystoreRedis


@dataclass
class ResourceInfo:
    infra_docs_url: str
    infra_name: str
    infra_lf_class: str
    django_settings: Optional[str]
    views_imports: Optional[str]
    django_test_endpoint: Optional[str]
    django_test_endpoint_url: Optional[str]
    requirements: List[str]
    installed_app: Optional[str]


resource_type_to_resource_info_kwargs = {
    # GCP Compute Engine Redis
    ComputeEngineRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/compute-engine#compute-engine-redis",
        "infra_name": "redis_vm",
        "infra_lf_class": "lf.gcp.ComputeEngineRedis",
        "django_settings": """CACHES = {
    "default": redis_vm.django_settings(),
}
""",
        "views_imports": "from django.core.cache import cache",
        "django_test_endpoint": """
# NOTE: This should normally use a POST request since it's modifying state, but we're
# using GET so you can easily test it in your browser.
@api_view(["GET"])
def test_redis(request, key):
    # Write to cache (Redis)
    cache.set(key, "Hello from Redis!", timeout=60)
    # Immediately read from cache to verify write
    return Response({"message": cache.get(key)})
""",
        "django_test_endpoint_url": 'path("test_redis/<key>", views.test_redis),',
        "requirements": ["redis>=4.2.0"],
        "installed_app": None,
    },
    # GCP Memorystore Redis
    MemorystoreRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/memorystore",
        "infra_name": "memorystore",
        "infra_lf_class": "lf.gcp.MemorystoreRedis",
        "django_settings": """CACHES = {
    "default": memorystore.django_settings(),
}
""",
        "views_imports": "from django.core.cache import cache",
        "django_test_endpoint": """
# NOTE: This should normally use a POST request since it's modifying state, but we're
# using GET so you can easily test it in your browser.
@api_view(["GET"])
def test_redis(request, key):
    # Write to cache (Redis)
    cache.set(key, "Hello from Redis!", timeout=60)
    # Immediately read from cache to verify write
    return Response({"message": cache.get(key)})
""",
        "django_test_endpoint_url": 'path("test_redis/<key>", views.test_redis),',
        "requirements": ["redis>=4.2.0"],
        "installed_app": None,
    },
    # GCP GCS Bucket
    GCSBucket: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/gcs-bucket",
        "infra_name": "gcs_bucket",
        "infra_lf_class": "lf.gcp.GCSBucket",
        "django_settings": """STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
    },
}
GS_BUCKET_NAME = gcs_bucket.outputs().bucket_name
GS_CREDENTIALS = lf.gcp.get_service_account_credentials()
""",
        "views_imports": "from django.core.files.storage import default_storage",
        "django_test_endpoint": """
# NOTE: This should normally use a POST request since it's modifying state, but we're
# using GET so you can easily test it in your browser.
@api_view(["GET"])
def test_gcs(request, object_name):
    # Write to GCS
    with default_storage.open(object_name, "w") as file:
        file.write("Hello from GCS!")
    # Immediately read from GCS to verify write
    with default_storage.open(object_name, "r") as file:
        return Response({"message": file.read()})
""",
        "django_test_endpoint_url": 'path("test_gcs/<object_name>", views.test_gcs),',
        "requirements": ["django-storages[google]"],
        "installed_app": "storages",
    },
    # GCP Cloud SQL (Postgres)
    CloudSQLPostgres: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/cloud-sql",
        "infra_name": "postgres",
        "infra_lf_class": "lf.gcp.CloudSQLPostgres",
        "django_settings": """DATABASES = {
    "default": postgres.django_settings(),
}
""",
        "views_imports": None,
        "django_test_endpoint": None,
        "django_test_endpoint_url": None,
        "requirements": ["psycopg2-binary"],
        "installed_app": None,
    },
    # AWS S3 Bucket
    S3Bucket: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/s3-bucket",
        "infra_name": "s3_bucket",
        "infra_lf_class": "lf.aws.S3Bucket",
        "views_imports": "from django.core.files.storage import default_storage",
        "django_settings": """STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
}
AWS_STORAGE_BUCKET_NAME = s3_bucket.outputs().bucket_name
""",
        "django_test_endpoint": """
# NOTE: This should normally use a POST request since it's modifying state, but we're
# using GET so you can easily test it in your browser.
@api_view(["GET"])
def test_s3(request, object_name):
    # Write to S3
    with default_storage.open(object_name, "w") as file:
        file.write("Hello from S3!")
    # Immediately read from S3 to verify write
    with default_storage.open(object_name, "r") as file:
        return Response({"message": file.read()})
""",
        "django_test_endpoint_url": 'path("test_s3/<object_name>", views.test_s3),',
        "requirements": ["django-storages[s3]"],
        "installed_app": "storages",
    },
    # AWS Elasticache Redis
    ElasticacheRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/elasticache-redis",
        "infra_name": "elasticache",
        "infra_lf_class": "lf.aws.ElasticacheRedis",
        "django_settings": """CACHES = {
    "default": elasticache.django_settings(),
}
""",
        "views_imports": "from django.core.cache import cache",
        "django_test_endpoint": """
# NOTE: This should normally use a POST request since it's modifying state, but we're
# using GET so you can easily test it in your browser.
@api_view(["GET"])
def test_redis(request, key):
    # Write to cache (Redis)
    cache.set(key, "Hello from Redis!", timeout=60)
    # Immediately read from cache to verify write
    return Response({"message": cache.get(key)})
""",
        "django_test_endpoint_url": 'path("test_redis/<key>", views.test_redis),',
        "requirements": ["redis>=4.2.0"],
        "installed_app": None,
    },
    # AWS RDS (Postgres)
    RDS: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/rds-postgres",
        "infra_name": "postgres",
        "infra_lf_class": "lf.aws.RDSPostgres",
        "views_imports": None,
        "django_settings": """DATABASES = {
    "default": postgres.django_settings(),
}
""",
        "django_test_endpoint": None,
        "django_test_endpoint_url": None,
        "requirements": ["psycopg2-binary"],
        "installed_app": None,
    },
}


def get_resource_info(resource: Type[Resource]) -> ResourceInfo:
    resource_info_kwargs = resource_type_to_resource_info_kwargs.get(resource, None)
    if resource_info_kwargs is None:
        raise ValueError(f"Unsupported resource type: {resource}")
    return ResourceInfo(**resource_info_kwargs)  # type: ignore


@dataclass
class DjangoProjectGenerator(ProjectGenerator):
    resources: List[Type[Resource]]
    # requirements.txt
    cloud_provider: Literal["aws", "gcp"]
    # launchflow.yaml
    launchflow_project_name: str
    launchflow_environment_name: str
    launchflow_service_name: str = "django-service"
    # Dockerfile
    python_major_version: int = sys.version_info.major
    python_minor_version: int = sys.version_info.minor
    port = 8080

    # The entire app/infra.py file
    @property
    def infra_dot_py(self) -> str:
        lines = [
            """\"\"\"
This is the recommended place to define all launchflow Resources, but you are free to
define them anywhere in your Python project.

To create find and create all resources in your current directory, run:
    $ lf create
\"\"\""""
        ]

        if len(self.resources) == 0:
            if self.cloud_provider == "aws":
                lines.extend(
                    [
                        f"""
# Uncomment the following line and run `lf create` to create an S3 bucket.
# s3_bucket = lf.aws.S3Bucket('{self.launchflow_project_name}-bucket')
"""
                    ]
                )
            elif self.cloud_provider == "gcp":
                lines.extend(
                    [
                        f"""
# Uncomment the following line and run `lf create` to create a GCS bucket.
# gcs_bucket = lf.gcp.GCSBucket('{self.launchflow_project_name}-bucket')
"""
                    ]
                )
            else:
                raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")
        else:
            lines.append("import launchflow as lf\n")
            for resource in self.resources:
                resource_info = get_resource_info(resource)
                lines.append(
                    f"""
# Docs: {resource_info.infra_docs_url}
{resource_info.infra_name} = {resource_info.infra_lf_class}('{self.launchflow_project_name}-{resource_info.infra_name.replace('_', '-')}')"""
                )
        return "\n".join(lines)

    # Used by django_app/settings.py
    @property
    def app_infra_imports(self) -> List[str]:
        # TODO: Clean this up so that each import is added separately then sort the
        # whole list at the end
        if len(self.resources) == 0:
            return ["import launchflow as lf"]
        to_return = ["import launchflow as lf"]
        infra_names = []

        for resource in self.resources:
            resource_info = get_resource_info(resource)
            infra_names.append(resource_info.infra_name)

        if len(infra_names) == 0:
            return to_return

        to_return.append(
            f"from django_app.infra import {', '.join(sorted(infra_names))}"
        )
        return to_return

    # Used by django_app/settings.py
    @property
    def app_django_settings(self) -> str:
        lines = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.django_settings is not None:
                lines.append(resource_info.django_settings)

        if self.cloud_provider == "gcp":
            lines.extend(
                [
                    "if lf.is_deployment():",
                    '    ALLOWED_HOSTS = ["*"]',
                    "    # TODO(developer): Replace this with your domain",
                    '    CSRF_TRUSTED_ORIGINS = ["https://*.run.app"]',
                    "    SECURE_SSL_REDIRECT = True",
                    '    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")',
                    "else:",
                    '    ALLOWED_HOSTS = ["*"]',
                    "    DEBUG = True",
                ]
            )
        elif self.cloud_provider == "aws":
            lines.extend(
                [
                    "if lf.is_deployment():",
                    '    ALLOWED_HOSTS = ["*"]',
                    "    # TODO(developer): Replace this with your domain's HTTPS URL",
                    '    CSRF_TRUSTED_ORIGINS = ["http://*.amazonaws.com"]',
                    # TODO: Add this once AWS services have HTTPS support
                    # "    SECURE_SSL_REDIRECT = True",
                    # "    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")",
                    "else:",
                    '    ALLOWED_HOSTS = ["*"]',
                    "    DEBUG = True",
                ]
            )
        return "\n".join(lines)

    # Used by django_app/settings.py
    @property
    def app_installed_apps(self) -> List[str]:
        installed_apps = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.installed_app is not None:
                installed_apps.append(resource_info.installed_app)
        return installed_apps

    # Used by app/urls.py
    @property
    def app_infra_urls(self) -> List[str]:
        urls = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.django_test_endpoint_url is not None:
                urls.append(resource_info.django_test_endpoint_url)
        return urls

    # Used by app/views.py
    @property
    def app_views_imports(self) -> List[str]:
        imports = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.views_imports is not None:
                imports.append(resource_info.views_imports)
        return imports

    # Used by app/views.py
    @property
    def app_infra_endpoints(self) -> List[str]:
        endpoints = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.django_test_endpoint is not None:
                endpoints.append(resource_info.django_test_endpoint)
        return endpoints

    # Used by requirements.txt
    @property
    def additional_requirements(self) -> List[str]:
        requirements = set()
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            requirements.update(resource_info.requirements)
        return "\n".join(sorted(requirements))  # type: ignore

    # Used by launchflow.yaml
    @property
    def launchflow_service_product(self) -> str:
        if self.cloud_provider == "aws":
            return "aws_ecs_fargate"
        elif self.cloud_provider == "gcp":
            return "gcp_cloud_run"
        raise ValueError(f"Unsupported cloud provider: {self.cloud_provider}")

    def template_path_info(self) -> Tuple[str, str]:
        template_dir = "launchflow.cli.gen.templates.django"
        template_name = "_simple_template"

        if CloudSQLPostgres in [resource for resource in self.resources] or RDS in [
            resource for resource in self.resources
        ]:
            template_name = "_postgres_template"

        return template_dir, template_name

    @property
    def docker_repository_prefix(self) -> str:
        if self.cloud_provider == "aws":
            return "public.ecr.aws/docker/library/"
        return ""

    def context(self) -> dict:
        return {
            # requirements.txt
            "cloud_provider": self.cloud_provider,
            "additional_requirements": self.additional_requirements,
            # launchflow.yaml
            "launchflow_project_name": self.launchflow_project_name,
            "launchflow_environment_name": self.launchflow_environment_name,
            "launchflow_service_name": self.launchflow_service_name,
            "launchflow_service_product": self.launchflow_service_product,
            # Dockerfile
            "docker_repository_prefix": self.docker_repository_prefix,
            "python_major_version": self.python_major_version,
            "python_minor_version": self.python_minor_version,
            "port": self.port,
            # django_app/infra.py
            "infra_dot_py": self.infra_dot_py,
            # django_app/settings.py
            "app_infra_imports": self.app_infra_imports,
            "app_django_settings": self.app_django_settings,
            "app_installed_apps": self.app_installed_apps,
            # app/migrations/*
            "current_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            # app/urls.py
            "app_infra_urls": self.app_infra_urls,
            # app/views.py
            "app_infra_endpoints": self.app_infra_endpoints,
            "app_views_imports": self.app_views_imports,
        }
