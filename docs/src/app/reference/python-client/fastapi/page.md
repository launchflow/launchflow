## \_AsyncSQLAlchemyDep

### setup

```python
_AsyncSQLAlchemyDep.setup(engine: AsyncEngine)
```

Sets up the async session maker with the provided engine.

**Args:**
- `engine (AsyncEngine)`: The SQLAlchemy async engine to use for creating the session.

### \_\_call\_\_

```python
async _AsyncSQLAlchemyDep.__call__()
```

Returns an async SQLAlchemy session.

**Raises:**
- `ValueError`: If the connection pool is not initialized.

## \_SQLAlchemyDep

### \_\_call\_\_

```python
_SQLAlchemyDep.__call__()
```

Returns a SQLAlchemy session.

**Raises:**
- `ValueError`: If the connection pool is not initialized.

#### sqlalchemy\_depends

```python
sqlalchemy_depends(engine: Engine, autocommit: bool = False, autoflush: bool = False, expire_on_commit: bool = False)
```

Returns a dependency that returns a SQLAlchemy Session for use in FastAPI.

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

#### sqlalchemy\_async\_depends

```python
sqlalchemy_async_depends(autocommit: bool = False, autoflush: bool = False, expire_on_commit: bool = False) -> _AsyncSQLAlchemyDep
```

Returns a dependency that returns a SQLAlchemy AsyncSession for use in FastAPI.

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
