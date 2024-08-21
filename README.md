<div align="center" style="display: flex; flex-direction: column; justify-content: center; margin-top: 16px; margin-bottom: 16px;">
    <a style="align-self: center" href="https://launchflow.com/#gh-dark-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-dark.png#gh-dark-mode-only">
    </a>
    <a style="align-self: center" href="https://launchflow.com/#gh-light-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-light.svg#gh-light-mode-only">
    </a>
    <div style="display: flex; align-content: center; gap: 4px; justify-content: center;   border-bottom: none;">
        <h2 style="margin-top: 0px; margin-bottom: 0px; border-bottom: none; text-align: start;">
            Deploy to AWS / GCP with Python
        </h2>
    </div>
</div>
<div style="text-align: center;" align="center">

📖 [Docs](https://docs.launchflow.com/) &nbsp; | &nbsp; ⚡ [Quickstart](https://docs.launchflow.com/docs/get-started) &nbsp; | &nbsp; 👋 [Slack](https://join.slack.com/t/launchflowusers/shared_invite/zt-27wlowsza-Uiu~8hlCGkvPINjmMiaaMQ)

</div>

[LaunchFlow](https://launchflow.com/) is an open source deployment tool that makes it easy to launch applications to Serverless, VMs, & Kubernetes on AWS and GCP (Azure coming soon).

Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated environment in your cloud account.

Fully customizable but configured by default - no messy YAML required.


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
