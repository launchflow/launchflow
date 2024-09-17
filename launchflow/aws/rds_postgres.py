# Handling imports and missing dependencies
try:
    import asyncpg  # type: ignore
except ImportError:
    asyncpg = None

try:
    import pg8000  # type: ignore
except ImportError:
    pg8000 = None

try:
    import psycopg2  # type: ignore
except ImportError:
    psycopg2 = None

try:
    from sqlalchemy.ext.asyncio import create_async_engine
except ImportError:
    create_async_engine = None  # type: ignore

try:
    from sqlalchemy import create_engine, event, text
except ImportError:
    text = None  # type: ignore
    event = None  # type: ignore
    create_engine = None  # type: ignore
    DeclarativeBase = None
    sessionmaker = None

import dataclasses

# Importing the required modules
import enum
from typing import Optional

import launchflow as lf
from launchflow.aws.resource import AWSResource
from launchflow.generic_clients import PostgresClient
from launchflow.models.enums import EnvironmentType, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Outputs
from launchflow.resource import ResourceInputs


# NOTE: AWS RDS only supports alphanumeric characters.
def _convert_resource_id_to_camel_case(s: str) -> str:
    # Split the string by both dashes and underscores, then capitalize each word
    # Finally, join them together without any separators to form CamelCase
    return "".join(word.capitalize() for word in s.replace("-", "_").split("_"))


@dataclasses.dataclass
class RDSPostgresOutputs(Outputs):
    endpoint: str
    username: str
    password: str
    port: int
    dbname: str
    region: str


class PostgresVersion(enum.Enum):
    POSTGRES9_3 = "9.3"
    POSTGRES9_4 = "9.4"
    POSTGRES9_5 = "9.5"
    POSTGRES9_6 = "9.6"
    POSTGRES10 = "10"
    POSTGRES11 = "11"
    POSTGRES12 = "12"
    POSTGRES13 = "13"
    POSTGRES14 = "14"
    POSTGRES15 = "15"
    POSTGRES16 = "16"


@dataclasses.dataclass
class RDSPostgresInputs(ResourceInputs):
    database_name: str
    publicly_accessible: bool
    instance_class: str
    allocated_storage_gb: int
    # If true the database will be made available in multiple availability zones
    highly_available: bool
    postgres_version: str
    postgres_family: str


class RDSPostgres(AWSResource[RDSPostgresOutputs], PostgresClient):
    """A Postgres cluster running on AWS's RDS service.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/rds/).

    ### Example Usage
    ```python
    from sqlalchemy import text
    import launchflow as lf

    # Automatically creates / connects to a RDS Postgres cluster in your AWS account
    postgres = lf.aws.RDSPostgres("my-pg-db")

    # Quick utilities for connecting to SQLAlchemy, Django, and other ORMs
    engine = postgres.sqlalchemy_engine()

    with engine.connect() as connection:
        print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
    ```
    """

    product = ResourceProduct.AWS_RDS_POSTGRES.value

    def __init__(
        self,
        name: str,
        *,
        allocated_storage_gb: int = 20,
        highly_available: Optional[bool] = None,
        instance_class: Optional[str] = None,
        publicly_accessible: Optional[bool] = None,
        postgres_version: PostgresVersion = PostgresVersion.POSTGRES16,
    ) -> None:
        """Create a new RDS Postgres resource.

        **Args:**
        - `name (str)`: The name of the RDS Postgres cluster.
        - `allocated_storage_gb (int)`: The amount of storage to allocate for the cluster in GB. Defaultus to 20 GB.
        - `highly_available (Optional[bool])`: Whether the database should be made available in multiple availability zones. Defaults to `False` for development environments and `True` for production.
        - `instance_class (Optional[str])`: The instance class to use for the RDS Postgres cluster. Defaults to `db.t4g.micro` for development environments and `db.r5.large` for production.
        - `publicly_accessible (Optionally[bool])`: Whether the database should be publicly accessible. Defaults to `True` for development environments and `False` for production.
        - `postgres_version (PostgresVersion)`: The version of Postgres to use. Defaults to `PostgresVersion.POSTGRES16`.
        """
        super().__init__(
            name=name, resource_id=f"{name}-{lf.project}-{lf.environment}".lower()
        )
        self.allocated_storage_gb = allocated_storage_gb
        self.highly_available = highly_available
        self.instance_class = instance_class
        self.publicly_accessible = publicly_accessible
        self.postgres_version = postgres_version

    def inputs(self, environment_state: EnvironmentState) -> RDSPostgresInputs:
        db_name = _convert_resource_id_to_camel_case(self.resource_id)
        if environment_state.environment_type == EnvironmentType.DEVELOPMENT:
            return RDSPostgresInputs(
                resource_id=self.resource_id,
                database_name=db_name,
                publicly_accessible=(
                    True
                    if self.publicly_accessible is None
                    else self.publicly_accessible
                ),
                instance_class=(
                    "db.t4g.micro"
                    if self.instance_class is None
                    else self.instance_class
                ),
                allocated_storage_gb=self.allocated_storage_gb,
                highly_available=(
                    False if self.highly_available is None else self.highly_available
                ),
                postgres_version=self.postgres_version.value,
                postgres_family=f"postgres{self.postgres_version.value}",
            )
        elif environment_state.environment_type == EnvironmentType.PRODUCTION:
            return RDSPostgresInputs(
                resource_id=self.resource_id,
                database_name=db_name,
                publicly_accessible=(
                    False
                    if self.publicly_accessible is None
                    else self.publicly_accessible
                ),
                instance_class=(
                    "db.r5.large"
                    if self.instance_class is None
                    else self.instance_class
                ),
                allocated_storage_gb=self.allocated_storage_gb,
                highly_available=(
                    True if self.highly_available is None else self.highly_available
                ),
                postgres_version=self.postgres_version.value,
                postgres_family=f"postgres{self.postgres_version.value}",
            )
        else:
            raise ValueError("unsupported environment type")

    def query(self, query: str):
        """Executes a SQL query on the Postgres instance running on the RDS cluster.

        **Args:**
        - `query (str)`: The SQL query to execute.

        **Returns:**
        - The result of the query if it returns rows, otherwise None.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.aws.RDSPostgres("my-pg-db")

        # Executes a query on the Postgres instance running on the RDS cluster
        postgres.query("SELECT 1")
        ```

        **NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.
        """
        engine = self.sqlalchemy_engine()
        with engine.connect() as connection:
            result = connection.execute(text(query))
            connection.commit()
            if result.returns_rows:
                return result.fetchall()

    def django_settings(self):
        """Returns a Django settings dictionary for connecting to the RDS Postgres instance.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.aws.RDSPostgres("my-pg-db")

        # settings.py
        DATABASES = {
            # Connect Django's ORM to the RDS Postgres instance
            "default": postgres.django_settings(),
        }
        ```
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Please install it with `pip install psycopg2`."
            )

        connection_info = self.outputs()
        return {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": connection_info.dbname,
            "USER": connection_info.username,
            "PASSWORD": connection_info.password,
            "HOST": connection_info.endpoint,
            "PORT": connection_info.port,
        }

    def sqlalchemy_engine_options(self):
        if pg8000 is None:
            raise ImportError(
                "pg8000 is not installed. Please install it with `pip install pg8000`."
            )

        connection_info = self.outputs()
        return {
            "url": f"postgresql+pg8000://{connection_info.username}:{connection_info.password}@{connection_info.endpoint}/{connection_info.dbname}",
        }

    async def sqlalchemy_async_engine_options(self):
        if asyncpg is None:
            raise ImportError(
                "asyncpg is not installed. Please install it with `pip install asyncpg`."
            )

        connection_info = await self.outputs_async()
        return {
            "url": f"postgresql+asyncpg://{connection_info.username}:{connection_info.password}@{connection_info.endpoint}/{connection_info.dbname}"
        }

    def sqlalchemy_engine(self, **engine_kwargs):
        """Returns a SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

        Args:
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.aws.RDSPostgres("my-pg-db")

        # Creates a SQLAlchemy engine for connecting to the RDS SQL Postgres instance
        engine = postgres.sqlalchemy_engine()

        with engine.connect() as connection:
            print(connection.execute("SELECT 1").fetchone())  # prints (1,)
        ```
        """
        if create_engine is None:
            raise ImportError(
                "SQLAlchemy is not installed. Please install it with "
                "`pip install sqlalchemy`."
            )

        engine_options = self.sqlalchemy_engine_options()
        engine_options.update(engine_kwargs)

        return create_engine(**engine_options)

    async def sqlalchemy_async_engine(self, **engine_kwargs):
        """Returns an async SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

        Args:
        - `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.aws.RDSPostgres("my-pg-db")

        # Creates an async SQLAlchemy engine for connecting to the RDS SQL Postgres instance
        engine = await postgres.sqlalchemy_async_engine()

        async with engine.connect() as connection:
            result = await connection.execute("SELECT 1")
            print(await result.fetchone())
        ```
        """
        if create_async_engine is None:
            raise ImportError(
                "SQLAlchemy asyncio extension is not installed. "
                "Please install it with `pip install sqlalchemy[asyncio]`."
            )

        engine_options = await self.sqlalchemy_async_engine_options()
        engine_options.update(engine_kwargs)

        return create_async_engine(**engine_options)
