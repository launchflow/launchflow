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
  name = var.env_role_name
}

# Create a task definition
resource "aws_ecs_task_definition" "task_definition" {
  family                   = "${var.resource_id}-task"
  task_role_arn            = data.aws_iam_role.launchflow_env_role.arn
  execution_role_arn       = data.aws_iam_role.launchflow_env_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  runtime_platform {
    operating_system_family = "LINUX"
  }
  cpu    = 256
  memory = 512

  container_definitions = jsonencode([
    {
      command    = ["/bin/sh -c 'echo \"<html> <head> <title>ECSFargateService(${var.resource_name})</title> <style>body {margin-top: 40px; background-color: #333;} </style> </head><body> <div style=color:white;text-align:center> <h1>ECSFargateService(${var.resource_name}) running in ${var.launchflow_environment}</h1> <h2>Congratulations!</h2> <p>Your application is now running on a container in Amazon ECS Fargate.</p> </div></body></html>\" >  /usr/local/apache2/htdocs/index.html && httpd-foreground'"]
      entryPoint = ["sh", "-c"]
      name       = var.resource_id
      image      = "httpd:2.4"
      cpu        = 256
      memory     = 512
      essential  = true
      portMappings = [
        {
          containerPort = var.port
          hostPort      = var.port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-create-group"  = "true"
          "awslogs-group"         = "/ecs/${var.resource_id}"
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
  name        = "${var.resource_id}-ecs-tasks-sg"
  description = "Allow inbound traffic"
  vpc_id      = var.vpc_id


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

resource "aws_security_group_rule" "ecs_alb_ingress" {
  count                    = var.alb_security_group_id != null ? 1 : 0
  type                     = "ingress"
  from_port                = var.port
  to_port                  = var.port
  protocol                 = "tcp"
  description              = "Allow inbound traffic from ALB"
  security_group_id        = aws_security_group.ecs_tasks_sg.id
  source_security_group_id = var.alb_security_group_id
}

resource "random_id" "rnd" {
  byte_length = 4
  keepers = {
    project_name = var.launchflow_project
    env_name     = var.launchflow_environment
    resource_id  = var.resource_id
  }
}


data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}

# Create an ECS Service
resource "aws_ecs_service" "ecs_service" {
  name                    = var.resource_id
  cluster                 = data.aws_ecs_cluster.ecs_cluster.id
  task_definition         = aws_ecs_task_definition.task_definition.arn
  desired_count           = var.desired_count
  launch_type             = "FARGATE"
  enable_ecs_managed_tags = true
  wait_for_steady_state   = true

  lifecycle {
    ignore_changes = [
      task_definition
    ]
  }

  network_configuration {
    subnets          = data.aws_subnets.lf_public_vpc_subnets.ids
    security_groups  = [aws_security_group.ecs_tasks_sg.id, data.aws_security_group.default_vpc_sg.id]
    assign_public_ip = true
  }

  dynamic "load_balancer" {
    for_each = var.alb_target_group_arn != null ? [1] : []
    content {
      target_group_arn = var.alb_target_group_arn
      container_name   = var.resource_id
      container_port   = var.port
    }
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
  depends_on = [
    aws_ecs_task_definition.task_definition
  ]
}


data "aws_network_interfaces" "interface_tags" {
  # Filter on service name
  filter {
    name   = "tag:aws:ecs:serviceName"
    values = [aws_ecs_service.ecs_service.name]
  }
  # Filter on cluster name
  filter {
    name   = "tag:aws:ecs:clusterName"
    values = [var.ecs_cluster_name]
  }

  depends_on = [
    aws_ecs_service.ecs_service
  ]
}

data "aws_network_interface" "first_interface" {
  id = data.aws_network_interfaces.interface_tags.ids[0]
}

output "public_ip" {
  value = data.aws_network_interface.first_interface.association[0].public_ip
}

output "aws_arn" {
  value = aws_ecs_service.ecs_service.id
}
