# TODO: we should let the user specify the port that the container is serving on
provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region     = var.aws_region
  default_tags {
    tags = {
      Project     = var.launchflow_project
      Environment = var.launchflow_environment
    }
  }
}

locals {
  # We truncate the string to ensure we don't go over name limits in AWS
  trunc_service_name = substr(var.service_name, 0, 15)
}

# Import the ECS Cluster
data "aws_ecs_cluster" "ecs_cluster" {
  cluster_name = var.ecs_cluster_name
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
  name = var.launchflow_env_role_name
}

# Create a task definition
resource "aws_ecs_task_definition" "task_definition" {

  family                   = "${var.launchflow_project}-${var.launchflow_environment}-${var.service_name}"
  task_role_arn            = data.aws_iam_role.launchflow_env_role.arn
  execution_role_arn       = data.aws_iam_role.launchflow_env_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256" # Modify as per your requirement
  memory                   = "512" # Modify as per your requirement

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.docker_image
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "LAUNCHFLOW_ARTIFACT_BUCKET"
          value = "s3://${var.artifact_bucket}"
        },
        {
          name  = "LAUNCHFLOW_PROJECT"
          value = var.launchflow_project
        },
        {
          name  = "LAUNCHFLOW_DEPLOYMENT_ID"
          value = var.launchflow_deployment_id
        },
        {
          name  = "LAUNCHFLOW_ENVIRONMENT"
          value = var.launchflow_environment
        },
        {
          name  = "LAUNCHFLOW_CLOUD_PROVIDER"
          value = "aws"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-create-group"  = "true"
          "awslogs-group"         = "/ecs/${var.launchflow_project}-${var.launchflow_environment}-${var.service_name}"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}


# Define a Security Group for the ECS Tasks
resource "aws_security_group" "ecs_tasks_sg" {
  name        = "${var.launchflow_project}-${var.launchflow_environment}-${var.service_name}-ecs-tasks-sg"
  description = "Allow inbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 8080
    to_port     = 8080
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

resource "random_id" "rnd" {
  byte_length = 4
  keepers = {
    project_name = var.launchflow_project
    env_name     = var.launchflow_environment
    service_name = var.service_name
  }
}


# Security group for ALB
resource "aws_security_group" "alb_sg" {
  name        = "${local.trunc_service_name}-${random_id.rnd.hex}-alb-sg"
  description = "Allow web traffic"
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

# Create an Application Load Balancer
resource "aws_lb" "alb" {

  name               = "${local.trunc_service_name}-${random_id.rnd.hex}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.aws_subnets.lf_public_vpc_subnets.ids

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

resource "aws_lb_target_group" "tg" {
  name        = "${local.trunc_service_name}-${random_id.rnd.hex}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tg.arn
  }
}

# Create an ECS Service
resource "aws_ecs_service" "ecs_service" {
  name            = "${var.launchflow_project}-${var.launchflow_environment}-${var.service_name}-ecs-service"
  cluster         = data.aws_ecs_cluster.ecs_cluster.id
  task_definition = aws_ecs_task_definition.task_definition.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  load_balancer {
    target_group_arn = aws_lb_target_group.tg.arn
    container_name   = var.service_name
    container_port   = 8080
  }

  network_configuration {
    subnets          = data.aws_subnets.lf_public_vpc_subnets.ids
    security_groups  = [aws_security_group.ecs_tasks_sg.id]
    assign_public_ip = true
  }

  depends_on = [
    aws_lb_listener.front_end,
  ]
}

output "service_url" {
  # TODO: setup an https listener
  value = "http://${aws_lb.alb.dns_name}"
}

output "aws_arn" {
  value = aws_ecs_service.ecs_service.id
}
