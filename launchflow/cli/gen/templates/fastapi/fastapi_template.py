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
    launchflow_imports: str
    infra_import: Optional[str]
    global_setup: Optional[str]
    fastapi_setup: Optional[str]
    app_imports: List[str]
    fastapi_test_endpoint: str
    requirements: List[str]


resource_type_to_resource_info_kwargs = {
    # GCP Compute Engine Redis
    ComputeEngineRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/compute-engine#compute-engine-redis",
        "infra_name": "redis_vm",
        "infra_lf_class": "lf.gcp.ComputeEngineRedis",
        "launchflow_imports": "",
        "infra_import": "from redis.asyncio import Redis",
        "global_setup": None,
        "fastapi_setup": None,
        "app_imports": [],
        "fastapi_test_endpoint": """
@app.post("/test_redis/{key}")
async def test_redis(
    key: str, value: str, redis_client: Redis = Depends(redis_vm.redis_async)
):
    # Write to Redis
    await redis_client.set(key, value)
    # Immediately read from Redis to verify the write
    value = await redis_client.get(key)
    return {"message": f"Set {key} to {value}"}
""",
        "requirements": ["redis>=4.2.0"],
    },
    # GCP Memorystore Redis
    MemorystoreRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/memorystore",
        "infra_name": "memorystore",
        "infra_lf_class": "lf.gcp.MemorystoreRedis",
        "launchflow_imports": "",
        "infra_import": "from redis.asyncio import Redis",
        "global_setup": None,
        "fastapi_setup": None,
        "app_imports": [],
        "fastapi_test_endpoint": """
@app.post("/test_redis/{key}")
async def test_redis(
    key: str, value: str, redis_client: Redis = Depends(memorystore.redis_async)
):
    # Write to Redis
    await redis_client.set(key, value)
    # Immediately read from Redis to verify the write
    value = await redis_client.get(key)
    return {"message": f"Set {key} to {value}"}
""",
        "requirements": ["redis>=4.2.0"],
    },
    # GCP GCS Bucket
    GCSBucket: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/gcs-bucket",
        "infra_name": "gcs_bucket",
        "infra_lf_class": "lf.gcp.GCSBucket",
        "launchflow_imports": "",
        "infra_import": None,
        "global_setup": None,
        "fastapi_setup": None,
        "app_imports": [],
        "fastapi_test_endpoint": """
# This endpoint uploads a file to GCS and reads it back to verify the bucket works
@app.post("/test_gcs/{object_name}")
async def test_gcs(object_name: str):
    # Write to GCS
    gcs_bucket.upload_from_string("Hello, World!", object_name)
    # Immediately read from GCS to verify the write
    gcs_bucket.download_file(object_name).decode("utf-8")
    return {"message": f"Uploaded {object_name} to GCS"}
""",
        "requirements": [],
    },
    # GCP Cloud SQL (Postgres)
    CloudSQLPostgres: {
        "infra_docs_url": "https://docs.launchflow.com/reference/gcp-resources/cloud-sql",
        "infra_name": "postgres",
        "infra_lf_class": "lf.gcp.CloudSQLPostgres",
        "launchflow_imports": "from launchflow.fastapi import sqlalchemy_async_depends",
        "infra_import": """from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
""",
        "global_setup": """# Create the global FastAPI dependency for the SQLAlchemy async session
async_session = sqlalchemy_async_depends()""",
        "app_imports": [
            "from app.models import Base, StorageUser",
            "from app.schemas import ListUsersResponse, UserResponse",
        ],
        "fastapi_setup": """    # Create the SQLAlchemy async engine (connection pool)
    engine = await postgres.sqlalchemy_async_engine()
    # Create the database tables using the engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Set up the FastAPI dependency
    async_session.setup(engine)""",
        "fastapi_test_endpoint": """
\"\"\"
The endpoints below define a simple CRUD API for a generic StorageUser model.

The StorageUser model is defined in app.models
The ListUsersResponse and UserResponse schemas are defined in app.schemas.
\"\"\"

@app.get("/users")
async def list_users(db: AsyncSession = Depends(async_session)):
    storage_users = (await db.execute(select(StorageUser))).scalars().all()
    return ListUsersResponse.from_storage(storage_users)


@app.post("/users")
async def create_user(email: str, name: str, db: AsyncSession = Depends(async_session)):
    storage_user = StorageUser(email=email, name=name)
    db.add(storage_user)
    await db.commit()
    return UserResponse.from_storage(storage_user)


@app.get("/users/{user_id}")
async def read_user(user_id: int, db: AsyncSession = Depends(async_session)):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_storage(storage_user)


@app.put("/users/{user_id}")
async def update_user(
    user_id: int, name: str, db: AsyncSession = Depends(async_session)
):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    storage_user.name = name
    await db.commit()
    return UserResponse.from_storage(storage_user)


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(async_session)):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(storage_user)
    await db.commit()
    return UserResponse.from_storage(storage_user)
""",
        "requirements": ["sqlalchemy[async]", "asyncpg"],
    },
    # AWS S3 Bucket
    S3Bucket: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/s3-bucket",
        "infra_name": "s3_bucket",
        "infra_lf_class": "lf.aws.S3Bucket",
        "launchflow_imports": "",
        "infra_import": "",
        "global_setup": None,
        "fastapi_setup": None,
        "app_imports": [],
        "fastapi_test_endpoint": """
# This endpoint uploads a file to S3 and reads it back to verify the bucket works
@app.post("/test_s3/{object_name}")
async def test_s3(object_name: str):
    # Write to S3
    s3_bucket.upload_from_string("Hello, World!", object_name)
    # Immediately read from S3 to verify the write
    s3_bucket.download_file(object_name).decode("utf-8")
    return {"message": f"Uploaded {object_name} to S3"}
""",
        "requirements": [],
    },
    # AWS Elasticache Redis
    ElasticacheRedis: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/elasticache-redis",
        "infra_name": "elasticache",
        "infra_lf_class": "lf.aws.ElasticacheRedis",
        "launchflow_imports": "",
        "infra_import": "from redis.asyncio import Redis",
        "global_setup": None,
        "fastapi_setup": None,
        "app_imports": [],
        "fastapi_test_endpoint": """
@app.post("/test_redis/{key}")
async def test_redis(
    key: str, value: str, redis_client: Redis = Depends(elasticache.redis_async)
):
    # Write to Redis
    await redis_client.set(key, value)
    # Immediately read from Redis to verify the write
    value = await redis_client.get(key)
    return {"message": f"Set {key} to {value}"}
""",
        "requirements": ["redis>=4.2.0"],
    },
    # AWS RDS (Postgres)
    RDS: {
        "infra_docs_url": "https://docs.launchflow.com/reference/aws-resources/rds-postgres",
        "infra_name": "postgres",
        "infra_lf_class": "lf.aws.RDSPostgres",
        "launchflow_imports": "from launchflow.fastapi import sqlalchemy_async_depends",
        "infra_import": """from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
""",
        "global_setup": """# Create the global FastAPI dependency for the SQLAlchemy async session
async_session = sqlalchemy_async_depends()""",
        "app_imports": [
            "from app.models import Base, StorageUser",
            "from app.schemas import ListUsersResponse, UserResponse",
        ],
        "fastapi_setup": """    # Create the SQLAlchemy async engine (connection pool)
    engine = await postgres.sqlalchemy_async_engine()
    # Create the database tables using the engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Set up the FastAPI dependency
    async_session.setup(engine)""",
        "fastapi_test_endpoint": """
\"\"\"
The endpoints below define a simple CRUD API for a generic StorageUser model.

The StorageUser model is defined in app.models
The ListUsersResponse and UserResponse schemas are defined in app.schemas.
\"\"\"

@app.get("/users")
async def list_users(db: AsyncSession = Depends(async_session)):
    storage_users = (await db.execute(select(StorageUser))).scalars().all()
    return ListUsersResponse.from_storage(storage_users)


@app.post("/users")
async def create_user(email: str, name: str, db: AsyncSession = Depends(async_session)):
    storage_user = StorageUser(email=email, name=name)
    db.add(storage_user)
    await db.commit()
    return UserResponse.from_storage(storage_user)


@app.get("/users/{user_id}")
async def read_user(user_id: int, db: AsyncSession = Depends(async_session)):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.from_storage(storage_user)


@app.put("/users/{user_id}")
async def update_user(
    user_id: int, name: str, db: AsyncSession = Depends(async_session)
):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    storage_user.name = name
    await db.commit()
    return UserResponse.from_storage(storage_user)


@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(async_session)):
    storage_user = await db.get(StorageUser, user_id)
    if storage_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(storage_user)
    await db.commit()
    return UserResponse.from_storage(storage_user)
""",
        "requirements": ["sqlalchemy[async]", "asyncpg"],
    },
}


def get_resource_info(resource: Type[Resource]) -> ResourceInfo:
    resource_info_kwargs = resource_type_to_resource_info_kwargs.get(resource, None)
    if resource_info_kwargs is None:
        raise ValueError(f"Unsupported resource type: {resource}")
    return ResourceInfo(**resource_info_kwargs)  # type: ignore


@dataclass
class FastAPIProjectGenerator(ProjectGenerator):
    resources: List[Type[Resource]]
    # requirements.txt
    cloud_provider: Literal["aws", "gcp"]
    # launchflow.yaml
    launchflow_project_name: str
    launchflow_environment_name: str
    launchflow_service_name: str = "fastapi-service"
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

    # Used by app/main.py
    @property
    def fastapi_imports(self) -> str:
        resource_set = set(self.resources)
        if len(resource_set) <= 1:
            return """from contextlib import asynccontextmanager

from fastapi import FastAPI"""
        if CloudSQLPostgres in resource_set or RDS in resource_set:
            return """from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException"""
        else:
            return """from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI"""

    # Used by app/main.py
    @property
    def app_infra_imports(self) -> List[str]:
        # TODO: Clean this up so that each import is added separately then sort the
        # whole list at the end
        if len(self.resources) == 0:
            return []
        to_return = []
        client_imports = []
        infra_names = []
        app_imports = []
        launchflow_imports = set()
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            infra_names.append(resource_info.infra_name)
            launchflow_imports.add(resource_info.launchflow_imports)
            app_imports.extend(resource_info.app_imports)
            if resource_info.infra_import is not None:
                client_imports.append(resource_info.infra_import)
        to_return.extend(sorted(client_imports))
        to_return.append("import launchflow")
        to_return.extend(sorted(launchflow_imports))
        to_return.append(f"from app.infra import {', '.join(sorted(infra_names))}")
        to_return.extend(sorted(app_imports))
        return to_return

    # Used by app/main.py
    @property
    def app_global_setup(self) -> str:
        lines = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            if resource_info.global_setup is not None:
                lines.append(resource_info.global_setup)
        return "\n".join(lines)

    # Used by app/main.py
    @property
    def app_infra_setup(self) -> str:
        if len(self.resources) == 0:
            return "\n".join(
                [
                    "# NOTE: This is where you connect resources on startup",
                    "    # For example, if you had a GCS bucket you would do:",
                    "    # await gcs_bucket.outputs()",
                ]
            )
        infra_names = []
        infra_steps = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            infra_names.append(resource_info.infra_name)
            if resource_info.fastapi_setup is not None:
                infra_steps.append(resource_info.fastapi_setup)
        return "\n".join(
            [
                "# Connects to all resources on startup",
                f"    await launchflow.connect_all({', '.join(infra_names)})",
            ]
            + infra_steps
        )

    # Used by app/main.py
    @property
    def app_infra_endpoints(self) -> List[str]:
        endpoints = []
        for resource in self.resources:
            resource_info = get_resource_info(resource)
            endpoints.append(resource_info.fastapi_test_endpoint)
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
        template_dir = "launchflow.cli.gen.templates.fastapi"
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
            # app/infra.py
            "infra_dot_py": self.infra_dot_py,
            # app/main.py
            "fastapi_imports": self.fastapi_imports,
            "app_infra_imports": self.app_infra_imports,
            "app_global_setup": self.app_global_setup,
            "app_infra_setup": self.app_infra_setup,
            "app_infra_endpoints": self.app_infra_endpoints,
        }
