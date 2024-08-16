---
title: Simple CRUD API
nextjs:
  metadata:
    title: Simple CRUD API
    description: Build a simple CRUD API with LaunchFlow
---

## Overview

In this example you can see how to build a simple CRUD API using LaunchFlow. All the source code for this example can be found on [GitHub](https://github.com/launchflow/launchflow-samples/tree/main/fastapi/gcp_simple_crud). This example will show you how to use LaunchFlow to create a Cloud SQL database to hold user information, and a GCS storage bucket to hold profile pictures.

## Code Walkthrough

There are three main files associated with our application:

{% tabProvider defaultLabel="infra.py" %}

{% tabs %}
{% tab label="infra.py" %}

`infra.py` is where we define the resource our application will use. In this case we define a Cloud SQL database and a GCS bucket. When you run `lf create` from the root directory of the project these resources will be created in the project and environment of your choice.

```python
import launchflow as lf

# TODO(developer): Set these variables with your own values
db = lf.gcp.CloudSQLPostgres("launchflow-demo-db")
lf_bucket = lf.gcp.GCSBucket("launchflow-demo-bucket-1")
```

{% /tab %}

{% tab label="main.py" %}

In the first block of code we:

1. Use the [sqlalchemy_engine](/reference/gcp-resources/cloud-sql#sqlalchemy-engine) function to create a SQLAlchemy engine from out LaunchFlow resource.
2. Create the database tables using the `Base.metadata.create_all` function.
3. Create a [FastAPI Dependency](https://fastapi.tiangolo.com/tutorial/dependencies/) using the [launchflow.fastapi.sqlalchemy] utility to ensure we can get a SQLAlchemy Session injected on every request.

```python,12
engine = pg.sqlalchemy_engine()
Base.metadata.create_all(bind=engine)
get_db = lf.fastapi.sqlalchemy(engine)

```

Now that we've set up everything for the database we can actually use them when we receive a request.

1. On line `38` we use the `get_db` dependency we defined above to have a SQLAlchemy session injected into our request.
2. On line `39` we can depend directly on the [bucket] method of our GCS bucket to get a reference to the bucket, and on like `45` we actually upload the image to the bucket.

```python,34,38,39,45
@app.post("/")
async def create_user(
    name: str,
    photo: UploadFile,
    db: Session = Depends(get_db),
    bucket: storage.Bucket = Depends(gcs_bucket.bucket),
):
    user = User(name=name, photo=photo.filename)
    db.add(user)
    db.commit()
    blob_path = f"users/{user.id}/{photo.filename}"
    bucket.blob(blob_path).upload_from_file(photo.file, content_type=photo.content_type)
    return user.__dict__
```

{% /tab %}

{% tab label="models.py" %}

`models.py` is where we setup our SQLAlchemy models. There is no LaunchFlow specific code in this file, but it will be consumed in `main.py`.

```python
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True)
    photo = Column(String)

```

{% /tab %}

{% /tabs %}
{% /tabProvider %}

## Running the application

{% callout type="warning" %}
To run this application make sure you update the `launchflow.yaml` to point to your own project and environment.
{% /callout %}

### Install the dependencies

```bash
pip install -r requirements.txt
```

### Login

To get started run login to LaunchFlow:

```bash
lf login
```

### Create Resources

NOTE: Before running make sure you update the bucket name in `infra.py` to be unique.

To create the resources needed to run the application, run:

```bash
lf create
```

This will prompt you to create a LaunchFlow project and environment to hold the resources. It takes GCP several minutes to provision your Cloud SQL database.

### Run the application

```bash
uvicorn app.main:app
```

Once running you can visit http://localhost:8000/docs to see the API documentation, and send requests.
