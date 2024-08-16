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

## CloudSQLDatabase

### initialization

Create a new Cloud SQL Database resource.

**Args:**
- `name (str)`: The name of the Cloud SQL Database.
- `cloud_sql_instance (CloudSQLPostgres)`: The Cloud SQL Postgres instance.

### inputs

```python
CloudSQLDatabase.inputs(environment_state: EnvironmentState) -> CloudSQLDatabaseInputs
```

Get the inputs for the Cloud SQL Database resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `CloudSQLDatabaseInputs`: The inputs for the Cloud SQL Database resource.

### query

```python
CloudSQLDatabase.query(query: str, user: Optional["CloudSQLUser"] = None)
```

Executes a query on the Cloud SQL Database instance.

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

### django\_settings

```python
CloudSQLDatabase.django_settings(user: Optional[CloudSQLUser] = None)
```

Returns a Django settings dictionary for connecting to the Cloud SQL Postgres instance.

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

### sqlalchemy\_engine\_options

```python
CloudSQLDatabase.sqlalchemy_engine_options(*, ip_type=None, user: Optional[CloudSQLUser] = None)
```

Get the SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

**Args:**
- `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
    For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
    Otherwise it will default to `IPTypes.PRIVATE`.
- `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

**Returns:**
- The SQLAlchemy engine options.

### sqlalchemy\_async\_engine\_options

```python
async CloudSQLDatabase.sqlalchemy_async_engine_options(ip_type=None, user: Optional[CloudSQLUser] = None)
```

Get the async SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

**Args:**
- `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
    For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
    Otherwise it will default to `IPTypes.PRIVATE`.
- `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

**Returns:**
- The async SQLAlchemy engine options.

### sqlalchemy\_engine

```python
CloudSQLDatabase.sqlalchemy_engine(*, ip_type=None, user: Optional[CloudSQLUser] = None, **engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

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

### sqlalchemy\_async\_engine

```python
async CloudSQLDatabase.sqlalchemy_async_engine(*, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

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

## CloudSQLUser

### initialization

Create a new Cloud SQL User resource.

**Args:**
- `name (str)`: The name of the Cloud SQL User.
- `cloud_sql_instance (CloudSQLPostgres)`: The Cloud SQL Postgres instance.
- `password (Optional[str])`: The password for the Cloud SQL User. Defaults to `None`.

### inputs

```python
CloudSQLUser.inputs(environment_state: EnvironmentState) -> CloudSQLUserInputs
```

Get the inputs for the Cloud SQL User resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `CloudSQLUserInputs`: The inputs for the Cloud SQL User resource.

## CloudSQLPostgres

A Postgres cluster running on Google Cloud SQL.

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

### initialization

Create a new Cloud SQL Postgres resource.

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

### inputs

```python
CloudSQLPostgres.inputs(environment_state: EnvironmentState) -> CloudSQLPostgresInputs
```

Get the inputs for the Cloud SQL Postgres resource.

**Args:**
- `environment_state (EnvironmentState)`: The environment to get inputs for

**Returns:**
- `CloudSQLPostgresInputs`: The inputs for the Cloud SQL Postgres resource.

### query

```python
CloudSQLPostgres.query(query: str, user: Optional["CloudSQLUser"] = None)
```

Executes a query on the Cloud SQL Postgres instance.

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

### django\_settings

```python
CloudSQLPostgres.django_settings(user: Optional["CloudSQLUser"] = None)
```

Returns a Django settings dictionary for connecting to the Cloud SQL Postgres instance.

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

### sqlalchemy\_engine\_options

```python
CloudSQLPostgres.sqlalchemy_engine_options(*, ip_type=None, user: Optional["CloudSQLUser"] = None)
```

Get the SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

**Args:**
- `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
    For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
    Otherwise it will default to `IPTypes.PRIVATE`.
- `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

**Returns:**
- The SQLAlchemy engine options.

### sqlalchemy\_async\_engine\_options

```python
async CloudSQLPostgres.sqlalchemy_async_engine_options(ip_type=None, user: Optional["CloudSQLUser"] = None)
```

Get the async SQLAlchemy engine options for connecting to the Cloud SQL Postgres instance.

**Args:**
- `ip_type`: The IP type to use for the connection. If not provided will default to the most permisive IP address.
    For example if your Cloud SQL instance is provisioned with a public IP address, the default will be `IPTypes.PUBLIC`.
    Otherwise it will default to `IPTypes.PRIVATE`.
- `user (CloudSQLUser)`: The `CloudSQLUser` to authenticate as. If not provided the default user for the instance will be used.

**Returns:**
- The async SQLAlchemy engine options.

### sqlalchemy\_engine

```python
CloudSQLPostgres.sqlalchemy_engine(*, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

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

### sqlalchemy\_async\_engine

```python
async CloudSQLPostgres.sqlalchemy_async_engine(*, ip_type=None, user: Optional["CloudSQLUser"] = None, **engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to the Cloud SQL Postgres instance.

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
