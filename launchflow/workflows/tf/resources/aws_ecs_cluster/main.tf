provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region              = var.aws_region
  default_tags {
    tags = {
      Project     = var.launchflow_project
      Environment = var.launchflow_environment
    }
  }
}

# Create the ECS Cluster
resource "aws_ecs_cluster" "ecs_cluster" {
  name = var.resource_id

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}


output "cluster_name" {
  value = aws_ecs_cluster.ecs_cluster.name
}

output "aws_arn" {
  value = aws_ecs_cluster.ecs_cluster.arn
}
