## RDS

A class for creating an RDS instance in AWS.

Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://docs.aws.amazon.com/rds/).

### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to an RDS cluster in your AWS account
rds_instance = lf.aws.RDS("my-db", engine_version=lf.aws.RDSEngineVersion.POSTGRES16)
```

### initialization

Create a new RDS resource.

**Args:**
- `name (str)`: The name of the RDS cluster.
- `allocated_storage_gb (int)`: The amount of storage to allocate for the cluster in GB. Defaults to 20 GB.
- `highly_available (Optional[bool])`: Whether the database should be made available in multiple availability zones. Defaults to `False` for development environments and `True` for production.
- `instance_class (Optional[str])`: The instance class to use for the RDS cluster. Defaults to `db.t4g.micro` for development environments and `db.r5.large` for production.
- `publicly_accessible (Optional[bool])`: Whether the database should be publicly accessible. Defaults to `True` for development environments and `False` for production.
- `engine_version (RDSEngineVersion)`: The engine version to use. Defaults to `RDSEngineVersion.POSTGRES16`.

### query

```python
RDS.query(query: str)
```

Executes a SQL query on the Postgres instance running on the RDS cluster.

**Args:**
- `query (str)`: The SQL query to execute.

**Returns:**
- The result of the query if it returns rows, otherwise None.

**Example usage:**
```python
import launchflow as lf

postgres = lf.aws.RDS("my-pg-db")

# Executes a query on the Postgres instance running on the RDS cluster
postgres.query("SELECT 1")
```

**NOTE**: This method is not recommended for production use. Use `sqlalchemy_engine` instead.

### sqlalchemy\_engine

```python
RDS.sqlalchemy_engine(**engine_kwargs)
```

Returns a SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

Args:
- `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

**Example usage:**
```python
import launchflow as lf

postgres = lf.aws.RDS("my-pg-db")

# Creates a SQLAlchemy engine for connecting to the RDS SQL Postgres instance
engine = postgres.sqlalchemy_engine()

with engine.connect() as connection:
    print(connection.execute("SELECT 1").fetchone())  # prints (1,)
```
