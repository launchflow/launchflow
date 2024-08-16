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
        bucket.delete_objects(Delete={"Objects": [{"Key": "test.txt"}]})
    return "success"


@app.get("/db")
async def get_db():
    engine = await infra.db.sqlalchemy_async_engine()

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return "success"


@app.get("/secret")
def get_secret():
    infra.secret.add_version("my-secret")

    result = infra.secret.version()

    assert result == "my-secret"
    return "success"


@app.get("/redis")
async def get_redis():
    r_client = await infra.redis.redis_async()
    await r_client.set("key", "value")

    result = await r_client.get("key")

    assert result == "value"
    return "success"


@app.get("/ec2_pg")
async def get_ec2_pg():
    engine = await infra.ec2_pg.sqlalchemy_async_engine()

    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    return "success"


@app.get("/ec2_redis")
async def get_ec2_redis():
    r_client = await infra.ec2_redis.redis_async()
    await r_client.set("key", "value")

    result = await r_client.get("key")

    assert result == "value"
    return "success"
