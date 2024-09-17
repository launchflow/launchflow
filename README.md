<div align="center" style="display: flex; flex-direction: column; justify-content: center; margin-top: 16px; margin-bottom: 16px;">
    <a style="align-self: center" href="https://launchflow.com/#gh-dark-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-dark.png#gh-dark-mode-only">
    </a>
    <a style="align-self: center" href="https://launchflow.com/#gh-light-mode-only" target="_blank">
        <img  height="auto" width="270" src="https://storage.googleapis.com/launchflow-public-images/launchflow-logo-light.svg#gh-light-mode-only">
    </a>
    <div style="display: flex; align-content: center; gap: 4px; justify-content: center;   border-bottom: none;">
        <h3 style="margin-top: 0px; margin-bottom: 0px; border-bottom: none; text-align: start;">
            Open Source Deployment Tool for AWS and GCP
        </h3>
    </div>
</div>
<div style="text-align: center;" align="center">

📖 [Docs](https://docs.launchflow.com/) &nbsp; | &nbsp; ⚡ [Quickstart](https://docs.launchflow.com/docs/get-started) &nbsp; | &nbsp; 👋 [Slack](https://join.slack.com/t/launchflowusers/shared_invite/zt-2pc3o5cbq-HZrMzlZXW2~Xs1CABbgPKQ)

</div>

[LaunchFlow](https://launchflow.com/) is an open source command line tool that deploys APIs, web apps, and other applications to AWS / GCP with minimal configuration. All of the deployment options are configured by default, but fully customizable with Python + Terraform.

- [x] **Serverless Deployments**
- [x] **Auto-Scaling VMs**
- [ ] **Kubernetes Clusters** (in preview)
- [ ] **Static Sites** (in preview)
- [x] **Terraform Resources**
- [ ] Pulumi Resources (coming soon)
- [ ] Custom Resources (coming soon)


Use the Python SDK to define your infrastructure in code, then run `lf deploy` to deploy everything to a dedicated VPC environment in your cloud account.


## 🧠 Concepts

### Services - [Docs](https://docs.launchflow.com/docs/concepts/services)

Services allow you to deploy APIs, web apps, background workers and other types of applications to your cloud account with minimal setup.

> [!NOTE]
> LaunchFlow is not just for deploying Python apps. The Python SDK is used to define your infrastructure in code, but you can deploy any application that runs on a VM, container, or serverless environment.
>
> <b>Python is just the language for your cloud configuration, similar to how Terraform uses HCL.</b>

_Click the dropdown below to see the service types that are currently supported._
<details>
<summary>
<strong>Services Types</strong>
</summary>

- Serverless APIs
  - [x] (AWS) Lambda Service - [Docs](https://docs.launchflow.com/reference/aws-services/lambda-service)
  - [x] (GCP) Cloud Run Service - [Docs](https://docs.launchflow.com/reference/gcp-services/cloud-run)
- Auto-Scaling VMs
  - [x] (AWS) ECS Fargate Service - [Docs](https://docs.launchflow.com/reference/aws-services/ecs-fargate)
  - [x] (GCP) Compute Engine Service - [Docs](https://docs.launchflow.com/reference/gcp-services/compute-engine-service)
- Kubernetes Clusters
  - [ ] (AWS) EKS - coming soon
  - [x] (GCP) GKE - [Docs](https://docs.launchflow.com/reference/gcp-services/gke-service)
- Static Websites
  - [ ] (AWS) S3 Static Site - coming soon
  - [ ] (GCP) GCS Static Site with Load Balancer - coming soon
  - [ ] (GCP) Firebase Static Site - coming soon

</details>



### Resources - [Docs](https://docs.launchflow.com/docs/concepts/resources)

Resources are the cloud services that your application uses, such as databases, storage, queues, and secrets. LaunchFlow provides a simple way to define, manage, and use these resources in your application.

_Click the dropdown below to see the resource types that are currently supported._
<details>
<summary>
<strong>Resource Types</strong>
</summary>

  - Cloud Storage
    - [x] (AWS) S3 Bucket - [Docs](https://docs.launchflow.com/reference/aws-resources/s3)
    - [x] (GCP) GCS Bucket - [Docs](https://docs.launchflow.com/reference/gcp-resources/gcs)
  - Databases (Postgres, MySQL, etc.)
    - [x] (AWS) RDS - [Docs](https://docs.launchflow.com/reference/aws-resources/rds)
    - [x] (GCP) Cloud SQL - [Docs](https://docs.launchflow.com/reference/gcp-resources/cloudsql)
  - Redis
    - [x] (AWS) ElastiCache Redis - [Docs](https://docs.launchflow.com/reference/aws-resources/elasticache)
    - [x] (GCP) Memorystore Redis - [Docs](https://docs.launchflow.com/reference/gcp-resources/memorystore)
  - Task Queues
    - [x] (AWS) SQS Queue - [Docs](https://docs.launchflow.com/reference/aws-resources/sqs)
    - [x] (GCP) Pub/Sub - [Docs](https://docs.launchflow.com/reference/gcp-resources/pubsub)
    - [x] (GCP) Cloud Tasks - [Docs](https://docs.launchflow.com/reference/gcp-resources/cloud-tasks)
  - Secrets
    - [x] (AWS) Secrets Manager - [Docs](https://docs.launchflow.com/reference/aws-resources/secrets-manager)
    - [x] (GCP) Secret Manager - [Docs](https://docs.launchflow.com/reference/gcp-resources/secret-manager)
  - Custom Domains
    - [ ] (AWS) Route 53 - coming soon
    - [x] (GCP) Custom Domain Mapping - [Docs](https://docs.launchflow.com/reference/gcp-resources/custom-domain-mapping)
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
api = lf.aws.ECSFargateService("my-api")
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
api = lf.aws.ECSFargateService("my-api", domain="your-domain.com", memory=512, cpu=256)
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
api = lf.aws.ECSFargateService("my-api", domain="your-domain.com")
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
api = lf.gcp.CloudRunService("my-api", domain="your-domain.com")
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


backend = lf.gcp.CloudRunService(
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
