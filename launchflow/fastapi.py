try:
    from sqlalchemy import Engine  # type: ignore
    from sqlalchemy.orm import Session, sessionmaker
except ImportError:
    Session = None  # type: ignore
    Engine = None  # type: ignore
    sessionmaker = None  # type: ignore


try:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
except ImportError:
    AsyncSession = None  # type: ignore
    AsyncEngine = None  # type: ignore
    async_sessionmaker = None  # type: ignore


class _AsyncSQLAlchemyDep:
    def __init__(self, autocommit: bool, autoflush: bool, expire_on_commit: bool):
        self.autocommit = autocommit
        self.autoflush = autoflush
        self.expire_on_commit = expire_on_commit

        self._SessionLocal = None

    def setup(
        self,
        engine: AsyncEngine,
    ):
        """Sets up the async session maker with the provided engine.

        **Args:**
        - `engine (AsyncEngine)`: The SQLAlchemy async engine to use for creating the session.
        """
        if self._SessionLocal is None:
            self._SessionLocal = async_sessionmaker(  # type: ignore
                bind=engine,
                autocommit=self.autocommit,
                autoflush=self.autoflush,
                expire_on_commit=self.expire_on_commit,
            )

    async def __call__(self):
        """Returns an async SQLAlchemy session.

        **Raises:**
        - `ValueError`: If the connection pool is not initialized.
        """
        if self._SessionLocal is None:
            raise ValueError(
                "Connection pool not initialized. Call `.setup(engine)` first."
            )
        db = self._SessionLocal()
        try:
            yield db
        finally:
            await db.close()


class _SQLAlchemyDep:
    def __init__(
        self,
        engine,
        autocommit: bool,
        autoflush: bool,
        expire_on_commit: bool,
    ):
        self._SessionLocal = sessionmaker(
            autocommit=autocommit,
            expire_on_commit=expire_on_commit,
            autoflush=autoflush,
            bind=engine,
        )

    def __call__(self):
        """Returns a SQLAlchemy session.

        **Raises:**
        - `ValueError`: If the connection pool is not initialized.
        """
        if self._SessionLocal is None:
            raise ValueError("Connection pool not initialized")
        db = self._SessionLocal()
        try:
            yield db
        finally:
            db.close()


def sqlalchemy_depends(
    engine: Engine,
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = False,
):
    """Returns a dependency that returns a SQLAlchemy Session for use in FastAPI.

    **Args:**
    - `engine (Engine)`: A SQLAlchemy engine to use for creating the session.
    - `autocommit (bool)`: Whether to autocommit the session after a commit.
    - `autoflush (bool)`: Whether to autoflush the session after a commit.
    - `expire_on_commit (bool)`: Whether to expire all instances after a commit.

    **Example usage:**
    ```python
    import launchflow as lf

    from fastapi import FastAPI, Depends
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    # Create the Postgres database instance
    postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

    # Create the SQLAlchemy engine (connection pool)
    engine = postgres.sqlalchemy_engine()

    # Create the FastAPI dependency
    session = lf.fastapi.sqlalchemy_depends(engine)

    app = FastAPI()

    @app.get("/")
    def read_root(db: Session = Depends(session)):
        # Use the session to query the database
        return db.execute(text("SELECT 1")).scalar_one_or_none()
    ```
    """
    if Session is None or sessionmaker is None:
        raise ImportError(
            "Requires `sqlalchemy` library, which is not installed. Install with `pip install sqlalchemy`."
        )
    return _SQLAlchemyDep(
        engine,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        autocommit=autocommit,
    )


def sqlalchemy_async_depends(
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = False,
) -> _AsyncSQLAlchemyDep:
    """Returns a dependency that returns a SQLAlchemy AsyncSession for use in FastAPI.

    **Args:**
    - `autocommit (bool)`: Whether to autocommit the session after a commit.
    - `autoflush (bool)`: Whether to autoflush the session after a commit.
    - `expire_on_commit (bool)`: Whether to expire all instances after a commit.

    **Example usage:**
    ```python
    from contextlib import asynccontextmanager

    import launchflow as lf

    from fastapi import FastAPI, Depends
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    # Create the Postgres database instance
    postgres = lf.gcp.CloudSQLPostgres("my-pg-db")

    # Create the FastAPI dependency
    async_session = lf.fastapi.sqlalchemy_async_depends()


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Create the SQLAlchemy async engine (connection pool)
        engine = await postgres.sqlalchemy_async_engine()
        # Setup the async session dependency
        async_session.setup(engine)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    async def query_postgres(db: AsyncSession = Depends(async_session)):
        # Use the async session to query the database
        return await db.execute(text("SELECT 1")).scalar_one_or_none()
    ```
    """
    if AsyncSession is None or async_sessionmaker is None:
        raise ImportError(
            "Requires `sqlalchemy` library, which is not installed. Install with `pip install sqlalchemy[asyncio]`."
        )
    return _AsyncSQLAlchemyDep(
        autocommit=autocommit, autoflush=autoflush, expire_on_commit=expire_on_commit
    )
