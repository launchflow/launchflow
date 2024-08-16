---
title: FastAPI
nextjs:
  metadata:
    title: FastAPI
    description: Use LaunchFlow with FastAPI
---

{% tabProvider defaultLabel="GCP" %}

## Overview

All of LaunchFlow's resource can be easily plugged in and used in your FastAPI application using [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/). Most resource clients can simply be injected as is. For example if you are using a GCS or S3 bucket you can do the following:

{% tabs %}
{% tab label="GCP" %}

_infra.py_

```python
import launchflow as lf

gcs_bucket = lf.gcp.GCSBucket('my-bucket')
```

_main.py_

```python
from app.infra import gcs_bucket
from fastapi import FastAPI, Depends
from google.cloud import storage

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root(bucket: storage.Bucket = Depends(gcs_bucket.bucket)) -> bytes:
    return bucket.blob("my-file").download_as_bytes()
```

You can also make use of FastAPI's [lifespan events](https://fastapi.tiangolo.com/advanced/events/) to fetch the connection info of your resources when your application starts up. After it's been fetched once, it'll be cached for subsequent uses:

_main.py_

```python,1,5+,6+,7+,8+
from app.infra import gcs_bucket
from fastapi import FastAPI, Depends
from google.cloud import storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    await gcs_bucket.outputs_async()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root(bucket: storage.Bucket = Depends(gcs_bucket.bucket)) -> bytes:
    return bucket.blob("my-file").download_as_bytes()
```

{% /tab %}

{% tab label="AWS" %}

_infra.py_

```python
import launchflow as lf

s3_bucket = lf.aws.S3Bucket('my-bucket')
```

_main.py_

```python
from app.infra import s3_bucket
from fastapi import FastAPI, Depends

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root(boto_bucket = Depends(s3_bucket.bucket)) -> bytes:
    return boto_bucket.Object("my-file").get()['Body'].read()
```

You can also make use of FastAPI's [lifespan events](https://fastapi.tiangolo.com/advanced/events/) to fetch the connection info of your resources when your application starts up. After it's been fetched once, it'll be cached for subsequent uses:

_main.py_

```python,1,4+,5+,6+,7+
from app.infra import s3_bucket
from fastapi import FastAPI, Depends

@asynccontextmanager
async def lifespan(app: FastAPI):
    await s3_bucket.outputs_async()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root(boto_bucket = Depends(s3_bucket.bucket)) -> bytes:
    return boto_bucket.Object("my-file").get()['Body'].read()
```
{% /tab %}

{% /tabs %}

## Complex Dependencies

LaunchFlow includes more complex dependencies in the [launchflow.fastapi](/reference/python-client/fastapi) package. This allows you to do things such as create a SQLAlchemy Session per request to your fast API application.

### SQLAlchemy

{% tabs %}
{% tab label="GCP" %}

_infra.py_

```python
import launchflow as lf

db = lf.gcp.CloudSQLPostgres("my-pg-db")
```

_main.py_

```python
from app.infra import db
from app.models import Base
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

db.outputs()
engine = db.sqlalchemy_engine()
Base.metadata.create_all(bind=engine)
get_db = launchflow.fastapi.sqlalchemy(engine)

app = FastAPI()

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    return db.execute(text("SELECT 1")).scalar_one_or_none()
```

{% /tab %}

{% tab label="AWS" %}

_infra.py_

```python
import launchflow as lf

db = lf.aws.RDSPostgres("my-pg-db")
```

_main.py_

```python
from app.infra import db
from app.models import Base
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

db.outputs()
engine = db.sqlalchemy_engine()
Base.metadata.create_all(bind=engine)
get_db = launchflow.fastapi.sqlalchemy(engine)

app = FastAPI()

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    return db.execute(text("SELECT 1")).scalar_one_or_none()
```

{% /tab %}

{% /tabs %}

{% /tabProvider %}
