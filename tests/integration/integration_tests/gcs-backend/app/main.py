import app.infra as infra
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/gcs_bucket")
def get_bucket_gcp():
    test_str = "hello world gcs"
    infra.bucket.upload_from_string(test_str, "test.txt")

    result = infra.bucket.download_file("test.txt")

    try:
        assert result.decode("utf-8") == test_str
    finally:
        bucket = infra.bucket.bucket()
        bucket.delete_blob("test.txt")
    return "success"
