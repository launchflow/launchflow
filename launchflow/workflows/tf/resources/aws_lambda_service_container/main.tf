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

# Import the subnets for the VPC
data "aws_subnets" "lf_public_vpc_subnets" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment,
    "Public" : "true"
  }
}

# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}

# Define a Security Group for the ECS Tasks
resource "aws_security_group" "ecs_tasks_sg" {
  name        = "${var.resource_id}-ecs-tasks-sg"
  description = "Allow inbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

# TODO: Determine if we should drop this rule since we already allow all VPC traffic
resource "aws_security_group_rule" "ecs_alb_ingress" {
    count                       = var.alb_security_group_id != null ? 1 : 0
    type                        = "ingress"
    from_port                   = 0
    to_port                     = 0
    protocol                    = "-1"
    description                 = "Allow inbound traffic from ALB"
    security_group_id           = aws_security_group.ecs_tasks_sg.id
    source_security_group_id    = var.alb_security_group_id
}

data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}
