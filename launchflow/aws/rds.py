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
    async_sessionmaker = None
    create_async_engine = None  # type: ignore

try:
    from sqlalchemy import create_engine, text
except ImportError:
    text = None  # type: ignore
    create_engine = None  # type: ignore
    DeclarativeBase = None
    sessionmaker = None

try:
    import pymysql  # type: ignore
except ImportError:
    pymysql = None

try:
    import aiomysql
except ImportError:
    aiomysql = None


import dataclasses
import enum
from typing import Optional

import launchflow as lf
from launchflow.aws.resource import AWSResource
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
class RDSOutputs(Outputs):
    endpoint: str
    username: str
    password: str
    port: int
    dbname: str
    region: str


class RDSEngine(enum.Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"


class RDSEngineVersion(enum.Enum):
    # PostgreSQL versions
    POSTGRES9_3 = ("9.3", RDSEngine.POSTGRES)
    POSTGRES9_4 = ("9.4", RDSEngine.POSTGRES)
    POSTGRES9_5 = ("9.5", RDSEngine.POSTGRES)
    POSTGRES9_6 = ("9.6", RDSEngine.POSTGRES)
    POSTGRES10 = ("10", RDSEngine.POSTGRES)
    POSTGRES11 = ("11", RDSEngine.POSTGRES)
    POSTGRES12 = ("12", RDSEngine.POSTGRES)
    POSTGRES13 = ("13", RDSEngine.POSTGRES)
    POSTGRES14 = ("14", RDSEngine.POSTGRES)
    POSTGRES15 = ("15", RDSEngine.POSTGRES)
    POSTGRES16 = ("16", RDSEngine.POSTGRES)

    # MySQL versions
    MYSQL5_6 = ("5.6", RDSEngine.MYSQL)
    MYSQL5_7 = ("5.7", RDSEngine.MYSQL)
    MYSQL8_0 = ("8.0", RDSEngine.MYSQL)

    def __init__(self, version: str, engine: RDSEngine):
        self.version = version
        self.engine = engine

    def family(self) -> str:
        return f"{self.engine.value}{self.version}"


@dataclasses.dataclass
class RDSInputs(ResourceInputs):
    database_name: str
    publicly_accessible: bool
    instance_class: str
    allocated_storage_gb: int
    highly_available: bool
    engine: str
    engine_version: str
    engine_family: str


class RDS(AWSResource[RDSOutputs]):
    """A class for creating an RDS instance in AWS.

    Like all [Resources](/docs/concepts/resources), this class configures itself across multiple [Environments](/docs/concepts/environments).

    For more information see [the official documentation](https://docs.aws.amazon.com/rds/).

    ### Example Usage
    ```python
    import launchflow as lf

    # Automatically creates / connects to an RDS cluster in your AWS account
    rds_instance = lf.aws.RDS("my-db", engine_version=lf.aws.RDSEngineVersion.POSTGRES16)
    ```
    """

    product = ResourceProduct.AWS_RDS.value

    def __init__(
        self,
        name: str,
        *,
        allocated_storage_gb: int = 20,
        highly_available: Optional[bool] = None,
        instance_class: Optional[str] = None,
        publicly_accessible: Optional[bool] = None,
        engine_version: RDSEngineVersion = RDSEngineVersion.POSTGRES16,
    ) -> None:
        """Create a new RDS resource.

        **Args:**
        - `name (str)`: The name of the RDS cluster.
        - `allocated_storage_gb (int)`: The amount of storage to allocate for the cluster in GB. Defaults to 20 GB.
        - `highly_available (Optional[bool])`: Whether the database should be made available in multiple availability zones. Defaults to `False` for development environments and `True` for production.
        - `instance_class (Optional[str])`: The instance class to use for the RDS cluster. Defaults to `db.t4g.micro` for development environments and `db.r5.large` for production.
        - `publicly_accessible (Optional[bool])`: Whether the database should be publicly accessible. Defaults to `True` for development environments and `False` for production.
        - `engine_version (RDSEngineVersion)`: The engine version to use. Defaults to `RDSEngineVersion.POSTGRES16`.
        """
        super().__init__(name=name, resource_id=f"{name}-{lf.environment}".lower())
        self.allocated_storage_gb = allocated_storage_gb
        self.highly_available = highly_available
        self.instance_class = instance_class
        self.publicly_accessible = publicly_accessible
        self.engine_version = engine_version

    def inputs(self, environment_state: EnvironmentState) -> RDSInputs:
        db_name = _convert_resource_id_to_camel_case(self.resource_id)
        if environment_state.environment_type == EnvironmentType.DEVELOPMENT:
            return RDSInputs(
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
                engine=self.engine_version.engine.value,
                engine_version=self.engine_version.version,
                engine_family=self.engine_version.family(),
            )
        elif environment_state.environment_type == EnvironmentType.PRODUCTION:
            return RDSInputs(
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
                engine=self.engine_version.engine.value,
                engine_version=self.engine_version.version,
                engine_family=self.engine_version.family(),
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

        postgres = lf.aws.RDS("my-pg-db")

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

    def sqlalchemy_engine_options(self):
        connection_info = self.outputs()
        if self.engine_version.engine == RDSEngine.MYSQL:
            if pymysql is None:
                raise ImportError(
                    "pymysql is not installed. Please install it with `pip install pymysql`."
                )
            return {
                "url": f"mysql+pymysql://{connection_info.username}:{connection_info.password}@{connection_info.endpoint}/{connection_info.dbname}",
            }

        elif self.engine_version.engine == RDSEngine.POSTGRES:
            if pg8000 is None:
                raise ImportError(
                    "pg8000 is not installed. Please install it with `pip install pg8000`."
                )
            return {
                "url": f"postgresql+pg8000://{connection_info.username}:{connection_info.password}@{connection_info.endpoint}/{connection_info.dbname}",
            }

    def sqlalchemy_engine(self, **engine_kwargs):
        """Returns a SQLAlchemy engine for connecting to the RDS SQL Postgres instance.

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
        """
        if create_engine is None:
            raise ImportError(
                "SQLAlchemy is not installed. Please install it with "
                "`pip install sqlalchemy`."
            )

        engine_options = self.sqlalchemy_engine_options()
        engine_options.update(engine_kwargs)

        return create_engine(**engine_options)
