import datetime

import infra
from fastapi import FastAPI
from sqlalchemy import text

app = FastAPI()


@app.get("/bucket")
def get_bucket():
    infra.bucket.upload_from_string("hello world", "test.txt")

    result = infra.bucket.download_file("test.txt")

    try:
        assert result.decode("utf-8") == "hello world"
    finally:
        bucket = infra.bucket.bucket()
        bucket.delete_blob("test.txt")
    return "success"


@app.get("/db")
async def get_db():
    engine = await infra.instance.sqlalchemy_async_engine()

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return "success"


@app.get("/secret")
def get_secret():
    infra.secret.add_version("my-secret".encode("utf-8"))

    result = infra.secret.version()

    assert result.decode("utf-8") == "my-secret"
    return "success"


@app.get("/redis")
async def get_redis():
    r_client = await infra.redis.redis_async()
    await r_client.set("key", "value")

    result = await r_client.get("key")

    assert result == "value"
    return "success"


@app.get("/gce_pg")
async def get_gce_pg():
    engine = await infra.gce_pg.sqlalchemy_async_engine()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return "success"


@app.get("/gce_redis")
async def get_gce_redis():
    r_client = await infra.gce_redis.redis_async()
    await r_client.set("key", "value")

    result = await r_client.get("key")

    assert result == "value"
    return "success"


@app.get("/custom_db")
async def custom_db():
    # Test custom database with default user
    start_time = datetime.datetime.now()
    engine = await infra.db2.sqlalchemy_async_engine()
    print(f"Time taken to create engine: {datetime.datetime.now() - start_time}")

    start_time = datetime.datetime.now()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    print(f"Time taken to connect to db: {datetime.datetime.now() - start_time}")
    print("\n\n\n")

    start_time = datetime.datetime.now()
    # Test custom database with custom user
    engine = await infra.db2.sqlalchemy_async_engine(user=infra.user)
    print(f"Time taken to create engine: {datetime.datetime.now() - start_time}")

    start_time = datetime.datetime.now()
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    print(f"Time taken to connect to db: {datetime.datetime.now() - start_time}")

    return "success"
