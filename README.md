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

📖 [Docs](https://docs.launchflow.com/) &nbsp; | &nbsp; ⚡ [Quickstart](https://docs.launchflow.com/docs/get-started) &nbsp; | &nbsp; 👋 [Slack](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ)

</div>

[LaunchFlow](https://launchflow.com/) is an open source Python SDK that lets you launch websites, APIs, and workers to AWS / GCP with minimal configuration.

- [x] **Serverless Deployments**
- [x] **Auto-Scaling VMs**
- [ ] **Kubernetes Clusters** (in preview)
- [ ] **Static Sites** (in preview)
- [x] **Terraform Resources**
- [ ] Pulumi Resources (coming soon)
- [ ] Custom Resources (coming soon)


Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated VPC environment in your cloud account.

Fully customizable but configured by default - no messy YAML required.

## 🧠 Concepts

### Services - [Docs](https://docs.launchflow.com/docs/concepts/services)

Services allow you to deploy websites, APIs, background workers and other types of applications to your cloud account with minimal setup.

> [!NOTE]
> LaunchFlow is not just for deploying Python apps. The Python SDK is used to define your infrastructure in code, but you can deploy any application that runs on a VM, container, or serverless environment.
>
> <b>Python is just the language for your cloud configuration, similar to how Terraform uses HCL.</b>

_Click the dropdown below to see the service types that are currently supported._
<details>
<summary>
<strong>Services Types</strong>
</summary>

- Static Websites
  - [ ] (AWS) S3 Static Site - coming soon
  - [ ] (GCP) GCS Static Site with Load Balancer - coming soon
  - [ ] (GCP) Firebase Static Site - coming soon
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

Environments group **Services** and **Resources** inside a private network (VPC) on either GCP or AWS. You can create multiple environments for different stages of your workflow (e.g. development, staging, production) and switch between them with a single command.

</details>

## ⚙️ Installation

```bash
pip install launchflow
```

## 🚀 Quickstart

### Deploy FastAPI to ECS Fargate on AWS:

#### Step 1. Create a new Python file (e.g. `main.py`) and add the following code:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'
```

#### Step 2. Add a Service type to your Python file:

```python
from fastapi import FastAPI
import launchflow as lf

app = FastAPI()

@app.get("/")
def index():
    return f'Hello from {lf.environment}!'

# Deploy this FastAPI app to ECS Fargate on AWS
api = lf.aws.ECSFargate("my-api")
```

#### Step 3. Run the `lf deploy` command to deploy your infrastructure:

```bash
lf deploy
```

#### This command will do the following:
1. Generate a Dockerfile and launchflow.yaml file <font size="-1">(if you don't have one)</font>
2. Create a new VPC (Environment) in your AWS account <font size="-1">(if you don't have one)</font>
3. Create a new ECS Fargate service and task definition <font size="-1">(if you don't have one)</font>
4. Create a new Application Load Balancer and Route 53 DNS record <font size="-1">(if you don't have one)</font>
5. Build a Docker image and push it to ECR
6. Deploy your FastAPI app to the new ECS Fargate service
7. Output the URL & DNS settings of your new FastAPI app

#### Step 4. Add a Resource type and customize the Service:

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

# You can customize the Fargate service with Python
api = lf.aws.ECSFargate("my-api", domain="your-domain.com", memory=512, cpu=256)
```

### Step 5. Run the `lf deploy` command to deploy your updated infrastructure:

```bash
lf deploy
```

## 📖 Examples

_Click the dropdowns below to see the example's code._

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
api = lf.aws.ECSFargate("my-api", domain="your-domain.com")
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
api = lf.gcp.CloudRun("my-api", domain="your-domain.com")
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
    "react-app", "./dst" domain=f"{lf.environment}.app.launchflow.com"
)

if __name__ == "__main__":
   # Use Python to easily automate non-Python applications
  print(f"Bucket URL: {bucket.url}")
```

</details>

<details>
<summary><b><font size="+1">Full on scripting with Python  (GCP)</font></b></summary>

> [!IMPORTANT]
> This example is not yet available in the LaunchFlow Python SDK.

```python
import launchflow as lf


backend = lf.gcp.CloudRun(
    "fastapi-api", domain=f"{lf.environment}.api.launchflow.com"
)

frontend = lf.gcp.BackendBucket(
    "react-static-app",
    static_directory="./dst",
    domain=f"{lf.environment}.console.launchflow.com",
    env={
        "LAUNCHFLOW_API_URL": backend.url
    }
)

result = lf.deploy(backend, frontend, environment="dev")

if not result.successful:
    print(result.error)
    exit(1)

print(f"Frontend URL: {frontend.url}")
print(f"Backend URL: {backend.url}")
```

</details>

## Don't see what you're looking for?
Reach out to team@launchflow.com to speed up development of the feature you need. Most of the unfinished features are already in development and can be completed in under a week - we just need to know what to prioritize!
