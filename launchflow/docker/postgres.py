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

from dataclasses import dataclass
from typing import Dict

from launchflow.docker.resource import DockerResource
from launchflow.node import Inputs, Outputs


@dataclass
class DockerPostgresOutputs(Outputs):
    container_id: str
    password: str
    ports: Dict[str, int]


@dataclass
class DockerPostgresInputs(Inputs):
    password: str
    ports: Dict[str, int]


class DockerPostgres(DockerResource[DockerPostgresOutputs]):
    def __init__(self, name: str, *, password: str = "password") -> None:
        """A Postgres resource running in a Docker container.

        **Args:**
        - `name` (str): The name of the Postgres resource. This must be globally unique.
        - `password` (str): The password for the Postgres DB. If not provided, a standard password will be used.

        **Example usage**:
        ```python
        from sqlalchemy import text
        import launchflow as lf

        postgres = lf.docker.Postgres("postgres-db")
        engine = postgres.sqlalchemy_engine()

        with engine.connect() as connection:
            print(connection.execute(text("SELECT 1")).fetchone())  # prints (1,)
        ```
        """
        self.password = password

        super().__init__(
            name=name,
            env_vars={
                "POSTGRES_PASSWORD": self.password,
                "POSTGRES_DB": "postgres",
                "POSTGRES_USER": "postgres",
            },
            command=None,
            ports={"5432/tcp": None},  # type: ignore
            docker_image="postgres",
            running_container_id=None,  # Lazy-loaded
        )

    def inputs(self, *args, **kwargs) -> DockerPostgresInputs:  # type: ignore
        self._lazy_load_container_info()
        return DockerPostgresInputs(ports=self.ports, password=self.password)

    def query(self, query: str):
        """Executes a SQL query on the Postgres instance running on the Docker container.

        Args:
        - `query`: The SQL query to execute.

        **Example usage:**
        ```python
        import launchflow as lf

        postgres = lf.docker.DockerPostgres("my-pg-db")

        # Executes a query on the Postgres instance running on the Docker container
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
        if psycopg2 is None:
            raise ImportError(
                "psycopg2 is not installed. Please install it with `pip install psycopg2`."
            )

        connection_info = self.outputs()
        return {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "postgres",
            "USER": "postgres",
            "PASSWORD": connection_info.password,
            "HOST": "localhost",
            "PORT": connection_info.ports["5432/tcp"],
        }

    def sqlalchemy_engine_options(self):
        if pg8000 is None:
            raise ImportError(
                "pg8000 is not installed. Please install it with `pip install pg8000`."
            )

        connection_info = self.outputs()
        return {
            "url": f"postgresql+pg8000://postgres:{connection_info.password}@localhost:{connection_info.ports['5432/tcp']}/postgres",
        }

    async def sqlalchemy_async_engine_options(self):
        if asyncpg is None:
            raise ImportError(
                "asyncpg is not installed. Please install it with `pip install asyncpg`."
            )

        connection_info = await self.outputs_async()
        return {
            "url": f"postgresql+asyncpg://postgres:{connection_info.password}@localhost:{connection_info.ports['5432/tcp']}/postgres"
        }

    def sqlalchemy_engine(self, **engine_kwargs):
        """Returns a SQLAlchemy engine for connecting to a postgres instance hosted on Docker.

        Args:
        - `**engine_kwargs`: Additional keyword arguments to pass to `sqlalchemy.create_engine`.

        **Example usage:**
        ```python
        import launchflow as lf
        db = lf.docker.Postgres("my-pg-db")
        engine = db.sqlalchemy_engine()
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
        """Returns an async SQLAlchemy engine for connecting to a postgres instance hosted on Docker.

        Args:
        - `**engine_kwargs`: Additional keyword arguments to pass to `create_async_engine`.

        **Example usage:**
        ```python
        import launchflow as lf
        db = lf.docker.Postgres("my-pg-db")
        engine = await db.sqlalchemy_async_engine()
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
