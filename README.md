<div align="center" style="display: flex; flex-direction: column; justify-content: center; margin-top: 16px; margin-bottom: 16px;">
    <a style="align-self: center" href="https://launchflow.com/#gh-dark-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-dark.png#gh-dark-mode-only">
    </a>
    <a style="align-self: center" href="https://launchflow.com/#gh-light-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-light.svg#gh-light-mode-only">
    </a>
    <div style="display: flex; align-content: center; gap: 4px; justify-content: center;   border-bottom: none;">
        <h3 style="margin-top: 0px; margin-bottom: 0px; border-bottom: none; text-align: start;">
            Deploy to AWS / GCP with Python
        </h3>
    </div>
</div>
<div style="text-align: center;" align="center">

📖 [Docs](https://docs.launchflow.com/) &nbsp; | &nbsp; ⚡ [Quickstart](https://docs.launchflow.com/docs/get-started) &nbsp; | &nbsp; 👋 [Slack](https://join.slack.com/t/launchflowusers/shared_invite/zt-27wlowsza-Uiu~8hlCGkvPINjmMiaaMQ)

</div>

[LaunchFlow](https://launchflow.com/) is an open source deployment tool that makes it easy to launch applications to Serverless, VMs, & Kubernetes on AWS and GCP.

Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated environment in your cloud account.

Fully customizable but configured by default - no messy YAML required.

## 🧠 Concepts

### Deployments - [Docs](https://docs.launchflow.com/docs/concepts/deployments)

Deployments allow you to deploy websites, APIs, background workers and other types of applications to your cloud account with minimal setup. There are 3 deployment types: **Services**, **Workers**, and **Jobs**.

> [!NOTE]
> LaunchFlow is not just for deploying Python apps. The Python SDK is used to define your infrastructure in code, but you can deploy any application that runs on a VM, container, or serverless environment.
>
> <b>Python is just the language for your DevOps automation.</b>

_Click the dropdowns below to see the deployment types that are currently supported._
<details>
<summary>
<strong>Services</strong> - Long-running applications that serve HTTP requests.
<a href="https://docs.launchflow.com/docs/concepts/deployments#services">Service Docs</a>
</summary>

- Static Websites
  - [ ] (AWS) S3 Backend - coming soon
  - [ ] (GCP) GCS Backend - coming soon
- Serverless APIs
  - [ ] (AWS) Lambda Service - coming soon
  - [x] (GCP) Cloud Run Service - [Docs](https://docs.launchflow.com/docs/services/gcp/cloud-run)
- Auto-Scaling VMs
  - [x] (AWS) ECS Fargate Service - [Docs](https://docs.launchflow.com/docs/services/aws/ec2-fargate) 
  - [x] (GCP) Compute Engine Service - [Docs](https://docs.launchflow.com/docs/services/gcp/compute-engine)
- Kubernetes Clusters
  - [ ] (AWS) EKS - coming soon
  - [x] (GCP) GKE - [Docs](https://docs.launchflow.com/docs/services/gcp/gke)

</details>

<details>
<summary>
<strong>Workers</strong> - Background workers that process tasks.
<a href="https://docs.launchflow.com/docs/concepts/deployments#workers">Worker Docs</a>
</summary>

- Serverless Workers
  - [ ] (AWS) Lambda Worker - coming soon
  - [ ] (GCP) Cloud Run Worker - coming soon
- Auto-Scaling VMs
  - [ ] (AWS) EC2 Worker - coming soon
  - [ ] (GCP) Compute Engine Worker - coming soon
- Kubernetes Clusters
  - [ ] (AWS) EKS Worker - coming soon
  - [ ] (GCP) GKE Worker - coming soon

</details>


<details>
<summary>
<strong>Jobs</strong> - One-off tasks that run to completion.
<a href="https://docs.launchflow.com/docs/concepts/deployments#jobs">Jobs Docs</a>
</summary>

- Serverless Jobs
  - [ ] (AWS) Lambda Job - coming soon
  - [ ] (GCP) Cloud Run Job - coming soon
- Auto-Scaling VMs
  - [ ] (AWS) EC2 Job - coming soon
  - [ ] (GCP) Compute Engine Job - coming soon
- Kubernetes Clusters
  - [ ] (AWS) EKS Job - coming soon
  - [ ] (GCP) GKE Job - coming soon

</details>


### Resources - [Docs](https://docs.launchflow.com/docs/concepts/resources)

Resources are the cloud services that your application uses, such as databases, storage, queues, and secrets. LaunchFlow provides a simple way to define, manage, and use these resources in your application.

_Click the dropdown below to see the resource types that are currently supported._
<details>
<summary>
<strong>Resource Types</strong>
</summary>

  - Cloud Storage
    - [x] (AWS) S3 Bucket - [Docs](https://docs.launchflow.com/docs/resources/aws/s3-bucket)
    - [x] (GCP) GCS Bucket - [Docs](https://docs.launchflow.com/docs/resources/gcp/gcs-bucket)
  - Postgres
    - [x] (AWS) RDS Postgres - [Docs](https://docs.launchflow.com/docs/resources/aws/rds-postgres)
    - [x] (GCP) Cloud SQL Postgres - [Docs](https://docs.launchflow.com/docs/resources/gcp/cloud-sql-postgres)
  - Redis
    - [x] (AWS) ElastiCache Redis - [Docs](https://docs.launchflow.com/docs/resources/aws/elasticache-redis)
    - [x] (GCP) Memorystore Redis - [Docs](https://docs.launchflow.com/docs/resources/gcp/memorystore-redis)
  - Task Queues
    - [x] (AWS) SQS Queue - [Docs](https://docs.launchflow.com/docs/resources/aws/sqs-queue)
    - [x] (GCP) Pub/Sub - [Docs](https://docs.launchflow.com/docs/resources/gcp/pubsub-topic)
    - [x] (GCP) Cloud Tasks - [Docs](https://docs.launchflow.com/docs/resources/gcp/cloud-tasks-queue)
  - Secrets
    - [x] (AWS) Secrets Manager - [Docs](https://docs.launchflow.com/docs/resources/aws/secrets-manager)
    - [x] (GCP) Secret Manager - [Docs](https://docs.launchflow.com/docs/resources/gcp/secret-manager)
  - Custom Domains
    - [x] (AWS) Route 53 - [Docs](https://docs.launchflow.com/docs/resources/aws/route53-domain)
    - [x] (GCP) Custom Domain Mapping - [Docs](https://docs.launchflow.com/docs/resources/gcp/custom-domain-mapping)
  - Monitoring & Alerts
    - [ ] (AWS) CloudWatch - coming soon
    - [ ] (GCP) StackDriver - coming soon
  - Custom Terraform Resources - coming soon
  - Custom Pulumi Resources - coming soon

</details>

### Environments - [Docs](https://docs.launchflow.com/docs/concepts/environments)

Environments group **Deployments** and **Resources** inside a private network (VPC) on either GCP or AWS. You can create multiple environments for different stages of your workflow (e.g. development, staging, production) and switch between them with a single command.

</details>

## ⚙️ Installation

```bash
pip install launchflow
```

## 🚀 Quickstart

### Step 1. Create a new Python file (e.g. `main.py`) and add the following code:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'
```

### Step 2. Add a Deployment type to your Python file:

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'

# Deploy this FastAPI app to ECS Fargate on AWS
api = lf.aws.ECSFargate("my-api", domain_name="launchflow.com")
```

### Step 3. Run the `lf deploy` command to deploy your infrastructure:

```bash
lf deploy
```

### This command will do the following:
1. Generate a Dockerfile and launchflow.yaml file <font size="-1">(if you don't have one)</font>
2. Create a new VPC (Environment) in your AWS account <font size="-1">(if you don't have one)</font>
3. Create a new ECS Fargate service and task definition <font size="-1">(if you don't have one)</font>
4. Create a new Application Load Balancer and Route 53 DNS record <font size="-1">(if you don't have one)</font>
5. Build a Docker image and push it to ECR
6. Deploy your FastAPI app to the new ECS Fargate service
7. Output the URL & DNS settings of your new FastAPI app

### Step 4. Add a Resource type to your Python file:

```python
from fastapi import FastAPI
import launchflow as lf

# Resource permissions are automatically configured for you
bucket = lf.gcp.S3Bucket("my-bucket")

app = FastAPI()

@app.get("/")
def index():
    bucket.upload_from_string(f"Hello from {lf.environment}!", "hello.txt")
    return bucket.download_file("hello.txt").decode()

# Deploy this FastAPI app to ECS Fargate on AWS
api = lf.aws.ECSFargate("my-api", domain_name="launchflow.com")
```

### Step 5. Run the `lf deploy` command to deploy your updated infrastructure:

```bash
lf deploy
```

## 📖 Examples

_Click the dropdowns below to see the deployment types that are currently supported._

<details open>
<summary><b><font size="+1">Deploy FastAPI to ECS Fargate (AWS)</font></b></summary>

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'

# Deploy this FastAPI app to ECS Fargate on AWS
api = lf.aws.ECSFargate("my-api", domain_name="launchflow.com")
```

</details>


<details>
<summary><b><font size="+1">Deploy FastAPI to Cloud Run (GCP)</font></b></summary>

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'

# Deploy Postgres hosted on (GCP) Cloud SQL 
api = lf.gcp.CloudRun("my-api", domain_name="launchflow.com")
```

</details>


<details>


<summary><b><font size="+1">Deploy Postgres to RDS & EC2 (AWS)</font></b></summary>

```python
import launchflow as lf

# Create / Connect to a Postgres Cluster on CloudSQL
postgres = lf.aws.RDSPostgres("postgres-cluster", disk_size_gb=10)

# Or on a Compute Engine VM
postgres = lf.aws.ComputeEnginePostgres("postgres-vm")

if __name__ == "__main__":
    # Built-in utility methods for using Postgres
    postgres.query("SELECT * FROM my_table")

    # Built-in connectors for Python ORMs
    postgres.sqlalchemy_engine()
    postgres.django_settings()
```

</details>

<details>
<summary><b><font size="+1">Deploy Postgres to Cloud SQL & Compute Engine (GCP)</font></b></summary>

```python
import launchflow as lf

# Create / Connect to a Postgres Cluster on CloudSQL
postgres = lf.gcp.CloudSQLPostgres("postgres-cluster", disk_size_gb=10)

# Or on a Compute Engine VM
postgres = lf.gcp.ComputeEnginePostgres("postgres-vm")

if __name__ == "__main__":
    # Built-in utility methods for using Postgres
    postgres.query("SELECT * FROM my_table")

    # Built-in connectors for Python ORMs
    postgres.sqlalchemy_engine()
    postgres.django_settings()
```

</details>

## 👀 Coming Soon

<details>
<summary><b><font size="+1">Deploy a static React app to a CDN (GCP)</font></b></summary>

> [!IMPORTANT]  
> This example is not yet available in the LaunchFlow Python SDK.

```python
import launchflow as lf

# Deploy a static React app to a GCS Bucket with a CDN
bucket = lf.gcp.BackendBucket(
    "react-app", domain="api.launchflow.com", use_cdn=True
)


if __name__ == "__main__":
   # Use Python to easily automate non-Python applications
  print(f"Bucket URL: {bucket.url}")
```

</details>

## Don't see what you're looking for?
Reach out to team@launchflow.com to speed up development of the feature you need. Most of the unfinished features are already in development and can be completed in under a week - we just need to know what to prioritize!