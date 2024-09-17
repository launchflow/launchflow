## RDSPostgres

A Postgres cluster running on AWS's RDS service.

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

### initialization

Create a new RDS Postgres resource.

**Args:**
- `name (str)`: The name of the RDS Postgres cluster.
- `allocated_storage_gb (int)`: The amount of storage to allocate for the cluster in GB. Defaultus to 20 GB.
- `highly_available (Optional[bool])`: Whether the database should be made available in multiple availability zones. Defaults to `False` for development environments and `True` for production.
- `instance_class (Optional[str])`: The instance class to use for the RDS Postgres cluster. Defaults to `db.t4g.micro` for development environments and `db.r5.large` for production.
- `publicly_accessible (Optionally[bool])`: Whether the database should be publicly accessible. Defaults to `True` for development environments and `False` for production.
- `postgres_version (PostgresVersion)`: The version of Postgres to use. Defaults to `PostgresVersion.POSTGRES16`.

### query

```python
RDSPostgres.query(query: str)
```

Executes a SQL query on the Postgres instance running on the RDS cluster.

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

### django\_settings

```python
RDSPostgres.django_settings()
```

Returns a Django settings dictionary for connecting to the RDS Postgres instance.

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

### sqlalchemy\_engine

```python
RDSPostgres.sqlalchemy_engine(**engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

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

### sqlalchemy\_async\_engine

```python
async RDSPostgres.sqlalchemy_async_engine(**engine_kwargs)
```

Returns an async SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

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
