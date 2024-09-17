"""
# Cloud SQL Resources

Resources for [Google Cloud SQL](https://cloud.google.com/sql). Available resources include:
- [`CloudSQLPostgres`](https://docs.launchflow.com/reference/gcp-resources/cloudsql#cloud-sql-postgres): A Postgres cluster running on Google Cloud SQL.
- [`CloudSQLUser`](https://docs.launchflow.com/reference/gcp-resources/cloudsql#cloud-sqluser): A user for a Cloud SQL Postgres instance.
- [`CloudSQLDatabase`](https://docs.launchflow.com/reference/gcp-resources/cloudsql#cloud-sql-database): A database for a Cloud SQL Postgres instance.

## Example Usage

### Create a Cloud SQL Postgres instance
```python
from sqlalchemy import text
import launchflow as lf

# Automatically creates / connects to a Cloud SQL Postgres cluster in your GCP project
postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

# Quick utilities for connecting to SQLAlchemy, Django, and other ORMs
engine = postgres.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
```

### Create a Cloud SQL Postgres instance with a custom database

```python
import launchflow as lf

postgres_instance = lf.gcp.CloudSQLPostgres("my-pg-db", include_default_db=False)
postgres_db = lf.gcp.CloudSQLDatabase("my-pg-db", cloud_sql_instance=postgres_instance)

postgres_db.query("SELECT 1")
```

### Create a Cloud SQL Postgres instance with a custom user and database

```python
import launchflow as lf

postgres_instance = lf.gcp.CloudSQLPostgres("my-pg-db", include_default_user=False, include_default_db=False)
postgres_user = lf.gcp.CloudSQLUser("my-pg-user", cloud_sql_instance=postgres_instance)
postgres_db = lf.gcp.CloudSQLDatabase("my-pg-db", cloud_sql_instance=postgres_instance)

postgres_db.query("SELECT 1", user=postgres_user)
```

"""

# Handling imports and missing dependencies
try:
    from google.cloud.sql.connector import Connector, IPTypes, create_async_connector
except ImportError:
    Connector = None  # type: ignore
    IPTypes = None  # type: ignore
    create_async_connector = None  # type: ignore

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
    from sqlalchemy import create_engine, text
except ImportError:
    create_engine = None  # type: ignore
    text = None  # type: ignore

# Importing the required modules

import dataclasses
import enum
from typing import Any, Dict, Literal, Optional, Tuple

import beaupy

from launchflow.gcp.resource import GCPResource
from launchflow.generic_clients import PostgresClient
from launchflow.models.enums import EnvironmentType, ResourceProduct
from launchflow.models.flow_state import EnvironmentState
from launchflow.node import Inputs, Outputs
from launchflow.resource import ResourceInputs


@dataclasses.dataclass
class CloudSQLPostgresOutputs(Outputs):
    connection_name: str
    user: str
    password: str
    database_name: str
    public_ip_address: str
    private_ip_address: str
    public_ip_enabled: bool


# TODO: Add Enums and other input types to generated docs.
# Punting for now since it goes to the top of the docs page - we need an option to
# have it go to the bottom.
class PostgresVersion(enum.Enum):
    POSTGRES_15 = "POSTGRES_15"
    POSTGRES_14 = "POSTGRES_14"
    POSTGRES_13 = "POSTGRES_13"
    POSTGRES_12 = "POSTGRES_12"
    POSTGRES_11 = "POSTGRES_11"
    POSTGRES_10 = "POSTGRES_10"
    POSTGRES_9_6 = "POSTGRES_9_6"


@dataclasses.dataclass
class DatabaseFlags(Inputs):
    key: str
    value: Any


@dataclasses.dataclass
class CloudSQLPostgresInputs(ResourceInputs):
    db_name: str
    disk_size_gb: int
    user_name: str
    deletion_protection: bool
    postgres_db_version: PostgresVersion
    postgres_db_tier: str
    postgres_db_edition: str
    allow_public_access: bool
    availability_type: str
    include_default_db: bool
    include_default_user: bool
    database_flags: Optional[Dict[str, Any]]


class CloudSQLPostgres(
    GCPResource[CloudSQLPostgresOutputs],
    PostgresClient,
):
    """A Postgres cluster running on Google Cloud SQL.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://cloud.google.com/sql/docs/).

    ### Example Usage

    ```python
    from sqlalchemy import text
    import launchflow as lf

    # Automatically creates / connects to a Cloud SQL Postgres cluster in your GCP project
    postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

    # Quick utilities for connecting to SQLAlchemy, Django, and other ORMs
    engine = postgres.sqlalchemy_engine()

    with engine.connect() as connection:
        print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
    ```
    """

    product = ResourceProduct.GCP_SQL_POSTGRES.value

    def __init__(
        self,
        name: str,
        *,
        disk_size_gb: int = 10,
        postgres_version: PostgresVersion = PostgresVersion.POSTGRES_15,
        include_default_db: bool = True,
        include_default_user: bool = True,
        delete_protection: bool = False,
        allow_public_access: Optional[bool] = None,
        edition: Literal["ENTERPRISE_PLUS", "ENTERPRISE"] = "ENTERPRISE",
        availability_type: Optional[Literal["REGIONAL", "ZONAL"]] = None,
        database_tier: Optional[str] = None,
        database_flags: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create a new Cloud SQL Postgres resource.

        **Args:**
        - `name (str)`: The name of the Cloud SQL Postgres instance.
        - `disk_size_gb (int)`: The size of the disk in GB. Defaults to `10`.
        - `postgres_version (PostgresVersion)`: The version of Postgres to use. Defaults to `PostgresVersion.POSTGRES_15`.
        - `include_default_db (bool)`: Whether to include a default database. Defaults to `True`.
        - `include_default_user (bool)`: Whether to include a default user. Defaults to `True`.
        - `delete_protection (bool)`: Whether to enable deletion protection. Defaults to `False`.
        - `allow_public_access (bool)`: Whether to allow public access. Default to `True` for development environments and `False` for production environments.
        - `edition (Literal["ENTERPRISE_PLUS", "ENTERPRISE"])`: The edition of the Cloud SQL Postgres instance. Defaults to `"ENTERPRISE"`.
        - `availability_type (Literal["REGIONAL", "ZONAL"])`: The availability type of the Cloud SQL Postgres instance. Defaults to `"ZONAL"` for developments environments and `"REGIONAL"` for production environments.
        - `database_tier (Literal["BASIC", "STANDARD_HA", "ENTERPRISE"])`: The tier of the Cloud SQL Postgres instance. Defaults to `"db-f1-micro"` for development environments and `"db-custom-1-3840"` for production environments.
        - `database_flags (Dict[Any, Any])`: Additional database flags to pass to your database instance. See: https://cloud.google.com/sql/docs/postgres/flags
        """
        super().__init__(
            name=name,
        )
        self.postgres_version = postgres_version
        self.include_default_db = include_default_db
        self.include_default_user = include_default_user
        self.delete_protection = delete_protection
        self.allow_public_access = allow_public_access
        self.edition = edition
        self.availability_type = availability_type
        self.database_tier = database_tier
        self.include_default_user = include_default_user
        self.disk_size_gb = disk_size_gb
        self.database_flags = database_flags
        self._default_db = None
        if include_default_db:
            self._default_db = CloudSQLDatabase(f"{name}-db", self)

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        imports = {
            "google_sql_database_instance.cloud_sql_instance": self.name,
        }
        if self.include_default_db:
            imports[
                "google_sql_database.cloud_sql_database[0]"
            ] = f"{self.name}/{self._default_db.name}"  # type: ignore
        if self.include_default_user:
            pw = beaupy.prompt(
                f"Please provide the password for user: `{self.name}-user` in db instance `{self.name}`:",
                secure=True,
            )
            if not pw:
                raise ValueError(f"A password is required for user `{self.name}-user`")
            imports["random_password.user-password[0]"] = pw
            imports[
                "google_sql_user.cloud_sql_user[0]"
            ] = f"{environment_state.gcp_config.project_id}/{self.name}/{self.name}-user"  # type: ignore
        return imports

    def inputs(self, environment_state: EnvironmentState) -> CloudSQLPostgresInputs:
        user_name = f"{self.name}-user"
        database_tier = self.database_tier
        if database_tier is None:
            database_tier = (
                "db-f1-micro"
                if environment_state.environment_type == EnvironmentType.DEVELOPMENT
                else "db-custom-1-3840"
            )
        allow_public_access = self.allow_public_access
        if allow_public_access is None:
            allow_public_access = (
                environment_state.environment_type == EnvironmentType.DEVELOPMENT
            )
        availability_type = self.availability_type
        if availability_type is None:
            availability_type = (
                "ZONAL"
                if environment_state.environment_type == EnvironmentType.DEVELOPMENT
                else "REGIONAL"
            )
        return CloudSQLPostgresInputs(
            resource_id=self.resource_id,
            db_name=self._default_db.name if self.include_default_db else None,  # type: ignore
            user_name=user_name,
            disk_size_gb=self.disk_size_gb,
            deletion_protection=self.delete_protection,
            postgres_db_version=self.postgres_version,
            postgres_db_tier=database_tier,
            postgres_db_edition=self.edition,
            allow_public_access=allow_public_access,
            availability_type=availability_type,
            include_default_db=self.include_default_db,
            include_default_user=self.include_default_user,
            database_flags=self.database_flags,
        )

    def query(self, query: str, user: Optional["CloudSQLUser"] = None):
        """Executes a query on the Cloud SQL Postgres instance.

        **Args:**
        - `query (str)`: The SQL query to execute.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - The results of the query.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # Executes a query on the Cloud SQL Postgres instance
        postgres.query("SELECT 1")
        ```

        **NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return self._default_db.query(query, user=user)  # type: ignore

    def django_settings(self, user: Optional["CloudSQLUser"] = None):
        """Returns a Django settings dictionary for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - A dictionary of Django settings for connecting to the Cloud SQL Postgres instance.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # settings.py
        DATABASES = {
            # Connect Django's ORM to the Cloud SQL Postgres instance
            "default": postgres.django_settings(),
        }
        ```
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return self._default_db.django_settings(user=user)  # type: ignore

    def sqlalchemy_engine_options(
        self, *, ip_type=None, user: Optional["CloudSQLUser"] = None
    ):
        """Get the SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - The SQLAlchemy engine options.
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return self._default_db.sqlalchemy_engine_options(ip_type=ip_type, user=user)  # type: ignore

    async def sqlalchemy_async_engine_options(
        self, ip_type=None, user: Optional["CloudSQLUser"] = None
    ):
        """Get the async SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - The async SQLAlchemy engine options.
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return await self._default_db.sqlalchemy_async_engine_options(  # type: ignore
            ip_type=ip_type, user=user
        )

    def sqlalchemy_engine(
        self, *, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs
    ):
        """Returns a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - The SQLAlchemy engine.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # Creates a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance
        engine = postgres.sqlalchemy_engine()

        with engine.connect() as connection:
            print(connection.execute("SELECT 1").fetchone())  # prints (1,)
        ```
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return self._default_db.sqlalchemy_engine(  # type: ignore
            ip_type=ip_type, user=user, **engine_kwargs
        )

    async def sqlalchemy_async_engine(
        self, *, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs
    ):
        """Returns an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - The async SQLAlchemy engine.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # Creates an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance
        engine = await postgres.sqlalchemy_async_engine()

        async with engine.begin() as connection:
            result = await connection.execute("SELECT 1")
            print(await result.fetchone())
        ```
        """
        if not self.include_default_db:
            raise ValueError(
                "Cannot connect to a Cloud SQL Postgres instance without a default database."
            )

        return await self._default_db.sqlalchemy_async_engine(  # type: ignore
            ip_type=ip_type, user=user, **engine_kwargs
        )


@dataclasses.dataclass
class CloudSQLUserInputs(ResourceInputs):
    cloud_sql_instance: str
    password: Optional[str]


@dataclasses.dataclass
class CloudSQLUserOutputs(Outputs):
    user: str
    password: str


class CloudSQLUser(GCPResource[CloudSQLUserOutputs]):
    product = ResourceProduct.GCP_SQL_USER.value

    def __init__(
        self,
        name: str,
        cloud_sql_instance: CloudSQLPostgres,
        password: Optional[str] = None,
    ) -> None:
        """Create a new Cloud SQL User resource.

        **Args:**
        - `name (str)`: The name of the Cloud SQL User.
        - `cloud_sql_instance (CloudSQLPostgres)`: The Cloud SQL Postgres instance.
        - `password (Optional[str])`: The password for the Cloud SQL User. Defaults to `None`.
        """
        super().__init__(
            name=name,
        )
        self.user = name
        self.cloud_sql_instance = cloud_sql_instance
        self.password = password
        self.depends_on(cloud_sql_instance)

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        imports = {}
        if self.password is None:
            pw = beaupy.prompt(
                f"Please provide the password for user: `{self.user}` in db instance: `{self.cloud_sql_instance.name}`:",
                secure=True,
            )
            if not pw:
                raise ValueError(f"A password is required for user `{self.user}`")
            imports["random_password.user-password"] = pw
        imports["google_sql_user.cloud_sql_user"] = (
            f"{environment_state.gcp_config.project_id}/{self.cloud_sql_instance.resource_id}/{self.resource_id}",  # type: ignore
        )

        return imports

    def outputs(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> CloudSQLUserOutputs:
        if self.password is None:
            return super().outputs(
                project=project, environment=environment, use_cache=use_cache
            )
        return CloudSQLUserOutputs(user=self.user, password=self.password)

    async def outputs_async(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> CloudSQLUserOutputs:
        if self.password is None:
            return await super().outputs_async(
                project=project, environment=environment, use_cache=use_cache
            )
        return CloudSQLUserOutputs(user=self.user, password=self.password)

    def inputs(self, environment_state: EnvironmentState) -> CloudSQLUserInputs:
        return CloudSQLUserInputs(
            resource_id=self.resource_id,
            cloud_sql_instance=self.cloud_sql_instance.resource_id,
            password=self.password,
        )


@dataclasses.dataclass
class CloudSQLDatabaseInputs(ResourceInputs):
    cloud_sql_instance: str


@dataclasses.dataclass
class CloudSQLDataBaseOutputs(Outputs):
    database_name: str


class CloudSQLDatabase(GCPResource[CloudSQLDataBaseOutputs]):
    product = ResourceProduct.GCP_SQL_DATABASE.value

    def __init__(self, name: str, cloud_sql_instance: CloudSQLPostgres) -> None:
        """Create a new Cloud SQL Database resource.

        **Args:**
        - `name (str)`: The name of the Cloud SQL Database.
        - `cloud_sql_instance (CloudSQLPostgres)`: The Cloud SQL Postgres instance.
        """
        super().__init__(
            name=name,
        )
        self.cloud_sql_instance = cloud_sql_instance
        self.depends_on(cloud_sql_instance)

    def outputs(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> CloudSQLDataBaseOutputs:
        return CloudSQLDataBaseOutputs(database_name=self.name)

    async def outputs_async(
        self,
        *,
        project: Optional[str] = None,
        environment: Optional[str] = None,
        use_cache: bool = True,
    ) -> CloudSQLDataBaseOutputs:
        return CloudSQLDataBaseOutputs(database_name=self.name)

    def inputs(self, environment_state: EnvironmentState) -> CloudSQLDatabaseInputs:
        return CloudSQLDatabaseInputs(
            resource_id=self.resource_id,
            cloud_sql_instance=self.cloud_sql_instance.resource_id,
        )

    def import_tofu_resource(
        self, environment_state: EnvironmentState
    ) -> Dict[str, str]:
        return {
            "google_sql_database.cloud_sql_database": f"{environment_state.gcp_config.project_id}/{self.cloud_sql_instance.resource_id}/{self.resource_id}"  # type: ignore
        }

    def _get_user_password(
        self,
        instance_connect: CloudSQLPostgresOutputs,
        user: Optional[CloudSQLUser] = None,
    ) -> Tuple[str, str]:
        """Get the user and password for the Cloud SQL Database resource.

        **Args:**
        - `instance_connect (CloudSQLPostgresOutputs)`: The Cloud SQL Postgres outputs.
        - `user (Optional[CloudSQLUser])`: The Cloud SQL User. Defaults to `None`.

        **Returns:**
        - `Tuple[str, str]`: The user and password.
        """
        if user is None:
            if not self.cloud_sql_instance.include_default_user:
                raise ValueError(
                    "Instance does not have a default user please provide the user to authenticate as"
                )
            user_name = instance_connect.user
            password = instance_connect.password
        else:
            user_connect = user.outputs()
            user_name = user_connect.user
            password = user_connect.password
        return user_name, password

    async def _get_user_password_async(
        self,
        instance_connect: CloudSQLPostgresOutputs,
        user: Optional[CloudSQLUser] = None,
    ) -> Tuple[str, str]:
        """Get the async user and password for the Cloud SQL Database resource.

        **Args:**
        - `instance_connect (CloudSQLPostgresOutputs)`: The Cloud SQL Postgres outputs.
        - `user (Optional[CloudSQLUser])`: The Cloud SQL User. Defaults to `None`.

        **Returns:**
        - `Tuple[str, str]`: The async user and password.
        """
        if user is None:
            if not self.cloud_sql_instance.include_default_user:
                raise ValueError(
                    "Instance does not have a default user please provide the user to authenticate as"
                )
            user_name = instance_connect.user
            password = instance_connect.password
        else:
            user_connect = await user.outputs_async()
            user_name = user_connect.user
            password = user_connect.password
        return user_name, password

    def query(self, query: str, user: Optional["CloudSQLUser"] = None):
        """Executes a query on the Cloud SQL Database instance.

        **Args:**
        - `query (str)`: The SQL query to execute.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLDatabase("my-pg-db")

        # Executes a query on the Cloud SQL Database instance
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

    def django_settings(self, user: Optional[CloudSQLUser] = None):
        """Returns a Django settings dictionary for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - A dictionary of Django settings for connecting to the Cloud SQL Postgres instance.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # settings.py
        DATABASES = {
            # Connect Django's ORM to the Cloud SQL Postgres instance
            "default": postgres.django_settings(),
        }
        ```
        """
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Please install it with `pip install psycopg2`."
            )

        instance_connect = self.cloud_sql_instance.outputs()
        user_name, password = self._get_user_password(instance_connect, user)
        host = instance_connect.private_ip_address
        if instance_connect.public_ip_enabled:
            host = instance_connect.public_ip_address

        return {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": self.name,
            "USER": user_name,
            "PASSWORD": password,
            "HOST": host,
            "SSLMODE": "require",
        }

    def sqlalchemy_engine_options(
        self, *, ip_type=None, user: Optional[CloudSQLUser] = None
    ):
        """Get the SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - The SQLAlchemy engine options.
        """
        if Connector is None or IPTypes is None:
            raise ImportError(
                "google-cloud-sql-connector not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        if pg8000 is None:
            raise ImportError(
                "pg8000 is not installed. Please install it with `pip install pg8000`."
            )
        instance_connect = self.cloud_sql_instance.outputs()
        user_name, password = self._get_user_password(instance_connect, user)
        if ip_type is None:
            if instance_connect.public_ip_enabled:
                ip_type = IPTypes.PUBLIC
            else:
                ip_type = IPTypes.PRIVATE

        connector = Connector(ip_type)

        # initialize Connector object for connections to Cloud SQL
        def getconn():
            conn = connector.connect(
                instance_connection_string=instance_connect.connection_name,
                driver="pg8000",
                user=user_name,
                password=password,
                db=self.name,
            )
            return conn

        return {"url": "postgresql+pg8000://", "creator": getconn}

    async def sqlalchemy_async_engine_options(
        self, ip_type=None, user: Optional[CloudSQLUser] = None
    ):
        """Get the async SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

        **Returns:**
        - The async SQLAlchemy engine options.
        """
        if Connector is None or IPTypes is None or create_async_connector is None:
            raise ImportError(
                "google-cloud-sql-connector not installed. Please install it with "
                "`pip install launchflow[gcp]`."
            )
        if asyncpg is None:
            raise ImportError(
                "asyncpg is not installed. Please install it with `pip install asyncpg`."
            )

        instance_connect = await self.cloud_sql_instance.outputs_async()
        user_name, password = await self._get_user_password_async(
            instance_connect, user
        )
        if ip_type is None:
            if instance_connect.public_ip_enabled:
                ip_type = IPTypes.PUBLIC
            else:
                ip_type = IPTypes.PRIVATE
        connector = await create_async_connector()

        # initialize Connector object for connections to Cloud SQL
        async def getconn():
            conn = await connector.connect_async(
                instance_connection_string=instance_connect.connection_name,
                driver="asyncpg",
                user=user_name,
                password=password,
                db=self.name,
                ip_type=ip_type,
            )
            return conn

        return {"url": "postgresql+asyncpg://", "async_creator": getconn}

    def sqlalchemy_engine(
        self, *, ip_type=None, user: Optional[CloudSQLUser] = None, **engine_kwargs
    ):
        """Returns a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - The SQLAlchemy engine.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # Creates a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance
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

        engine_options = self.sqlalchemy_engine_options(ip_type=ip_type, user=user)
        engine_options.update(engine_kwargs)

        return create_engine(**engine_options)

    async def sqlalchemy_async_engine(
        self, *, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs
    ):
        """Returns an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

        **Args:**
        - `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
            For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
            Otherwise it will default to `IPTypes.PRIVATE`.
        - `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Returns:**
        - The async SQLAlchemy engine.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

        # Creates an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance
        engine = await postgres.sqlalchemy_async_engine()

        async with engine.begin() as connection:
            result = await connection.execute("SELECT 1")
            print(await result.fetchone())
        ```
        """
        if create_async_engine is None:
            raise ImportError(
                "SQLAlchemy asyncio extension is not installed. "
                "Please install it with `pip install sqlalchemy[asyncio]`."
            )

        engine_options = await self.sqlalchemy_async_engine_options(
            ip_type=ip_type, user=user
        )
        engine_options.update(engine_kwargs)

        return create_async_engine(**engine_options)
