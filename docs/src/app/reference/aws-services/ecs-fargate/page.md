## ECSFargate

A service hosted on AWS ECS Fargate.

Like all [Services](/docs/concepts/services), this class configures itself across multiple [Environments](/docs/concepts/environments).

For more information see [the official documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html).


### Example Usage
```python
import launchflow as lf

# Automatically creates / connects to an ECS Fargate Service in your AWS account
service = lf.aws.ECSFargate("my-service")
```

**NOTE:** This will create the following infrastructure in your AWS account:
- A [ECS Fargate](https://aws.amazon.com/fargate/) service with the specified configuration.
- An [Application Load Balancer](https://aws.amazon.com/elasticloadbalancing) to route traffic to the service.
- A [Code Build](https://aws.amazon.com/codebuild) project that builds and deploys Docker images for the service.
- An [Elastic Container Registry](https://aws.amazon.com/ecr) repository to store the service's Docker image.

### initialization

Creates a new ECS Fargate service.

**Args:**
- `name (str)`: The name of the service.
- `ecs_cluster (Union[ECSCluster, str])`: The ECS cluster or the name of the ECS cluster.
- `cpu (int)`: The CPU units to allocate to the container. Defaults to 256.
- `memory (int)`: The memory to allocate to the container. Defaults to 512.
- `port (int)`: The port the container listens on. Defaults to 80.
- `desired_count (int)`: The number of tasks to run. Defaults to 1.
- `build_directory (str)`: The directory to build the service from. This should be a relative path from the project root where your `launchflow.yaml` is defined.
- `dockerfile (str)`: The Dockerfile to use for building the service. This should be a relative path from the `build_directory`.
- `build_ignore (List[str])`: A list of files to ignore when building the service. This can be in the same syntax you would use for a `.gitignore`.
- `domain (Optional[str])`: The domain name to use for the service. This will create an ACM certificate and configure the ALB to use HTTPS.
