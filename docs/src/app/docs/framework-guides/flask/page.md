---
title: Flask
nextjs:
  metadata:
    title: Flask
    description: Use LaunchFlow with Flask
---

{% tabProvider defaultLabel="GCP" %}

## Overview

All of LaunchFlow's resource can be easily plugged in and used in your Flask application with most working out of the box. For more complex dependencies, like Postgres, LaunchFlow includes utilities to help you plug into Flask extensions, like [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/).

For all resources you can call `.outputs()` at the start of your application to connect to them to your Flask application.

Most resource clients can simply be injected as is. For example if you are using a GCS or S3 bucket you can do the following:

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
from flask import Flask

app = Flask(__name__)

# Connect to the bucket on startup
gcs_bucket.outputs()

@app.route("/", methods=["GET"])
def read_root() -> str:
  return gcs_bucket.download_file(file_name).decode("utf-8")
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
from flask import Flask

app = Flask(__name__)

# Connect to the bucket on startup
s3_bucket.outputs()

@app.route("/", methods=["GET"])
def read_root() -> str:
  return s3_bucket.download_file(file_name).decode("utf-8")
```

{% /tab %}

{% /tabs %}

## Complex Dependencies

LaunchFlow includes utilities for more complex dependencies like Postgres. For example, if you are using Flask-SQLAlchemy you can use the `sqlalchemy_engine_options` methods on Postgres resources to get the SQLAlchemy engine options.

### SQLAlchemy

{% tabs %}
{% tab label="GCP" %}

_infra.py_

```python
import launchflow as lf

postgres = lf.gcp.CloudSQLPostgres("my-pg-db")
```

_main.py_

```python
from app.infra import postgres
from app.models import Base, StorageUser
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session

app = Flask(__name__)

db = SQLAlchemy(
    app,
    model_class=Base,
    engine_options=postgres.sqlalchemy_engine_options(),
)

with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def list_users():
    storage_users = db.session.execute(select(StorageUser)).scalars().all()
    return jsonify([{"id": user.id, "name": user.name} for user in storage_users])
```

{% /tab %}

{% tab label="AWS" %}

_infra.py_

```python
import launchflow as lf

postgres = lf.aws.RDSPostgres("my-pg-db")
```

_main.py_

```python
from app.infra import postgres
from app.models import Base, StorageUser
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session

app = Flask(__name__)

db = SQLAlchemy(
    app,
    model_class=Base,
    engine_options=postgres.sqlalchemy_engine_options(),
)

with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def list_users():
    storage_users = db.session.execute(select(StorageUser)).scalars().all()
    return jsonify([{"id": user.id, "name": user.name} for user in storage_users])
```

{% /tab %}

{% /tabs %}

{% /tabProvider %}
