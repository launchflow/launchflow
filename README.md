<div align="center">

<img src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo.svg" style="width: 75px; height: 75px;" alt="LaunchFlow Logo" /><h1>LaunchFlow</h1>

<hr>

### **🚀 Python-native infrastructure for the cloud 🚀⚒️**

📖 [Docs](https://docs.launchflow.com/) &nbsp; | &nbsp; ⚡ [Quickstart](https://docs.launchflow.com/quickstart) &nbsp; | &nbsp; 👋 [Slack](https://join.slack.com/t/launchflowusers/shared_invite/zt-27wlowsza-Uiu~8hlCGkvPINjmMiaaMQ)

</div>

LaunchFlow's Python SDK allows you to create and connect to cloud infrastructure in your own account on GCP, AWS, and Azure.

## 🤔 What is LaunchFlow?

LaunchFlow enables you to instantly provision cloud resources and deploy your python backend to the cloud of your choice (GCP, AWS, and Azure) all from python code.

## ⚙️ Installation

```bash
pip install launchflow
```

## 📖 Examples

### GCP Cloud Storage Bucket

1. Define a GCS Bucket

```python
import launchflow as lf

bucket = lf.gcp.GCSBucket("my-bucket")
```

2. Create the GCS bucket in your project

```
launchflow create
```

3. Use the Cloud SQL instance in your application

```python
from infra import bucket

bucket.blob("my-file").upload_from_filename("my-file")
```

### GCP Cloud SQL

1. Define a Cloud SQL instance

```python
import launchflow as lf

db = lf.gcp.CloudSQLPostgres("my-pg-db")
```

2. Create the Cloud SQL instance in your project

```
launchflow create
```

3. Use the Cloud SQL instance in your application

```python
from infra import db

engine = db.sqlalchemy_engine()
```

### FastAPI Integration

Built-in dependencies can easily be injected into your FastAPI application.

```python
from fastapi import FastAPI, Depends
import launchflow
from sqlalchemy import text

db = launchflow.gcp.CloudSQLPostgres("my-pg-db")
engine = db.sqlalchemy_engine()
get_db = launchflow.fastapi.sqlalchemy(engine)

app = FastAPI()

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    return db.execute(text("SELECT 1")).scalar_one_or_none()
```
