provider "aws" {
  region              = var.aws_region
  allowed_account_ids = [var.aws_account_id]

  default_tags {
    tags = {
      Project     = var.launchflow_project
      Environment = var.launchflow_environment
    }
  }
}

data "aws_s3_bucket" "artifact_bucket" {
  bucket = var.artifact_bucket_name
}

data "aws_availability_zones" "available" {}

locals {
  az_names = slice(data.aws_availability_zones.available.names, 0, 3)
  subnet_blocks = merge({
    for i, az in local.az_names : "${az}-public" => cidrsubnet(aws_vpc.env_vpc.cidr_block, 4, i * 2)
    }, {
    for i, az in local.az_names : "${az}-private" => cidrsubnet(aws_vpc.env_vpc.cidr_block, 4, i * 2 + 1)
  })
}

# This is the role that all services will use to run
# And will be used to authenticate with all resources
resource "aws_iam_role" "env_role" {
  name = "${var.launchflow_project}-${var.launchflow_environment}-role"

  # Terraform's "jsonencode" function converts a
  # Terraform expression result to valid JSON syntax.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      },
    ]
  })

  inline_policy {
    name = "${var.launchflow_project}-${var.launchflow_environment}-artifact-bucket-access"

    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Action = [
            "ec2:DescribeNetworkInterfaces",
            "ec2:CreateNetworkInterface",
            "ec2:DeleteNetworkInterface",
            "ec2:DescribeInstances",
            "ec2:AttachNetworkInterface"
          ]
          Effect   = "Allow"
          Resource = "*"
        },
        {
          Action = [
            "s3:*",
          ]
          Effect = "Allow"
          Resource = [
            "${data.aws_s3_bucket.artifact_bucket.arn}",
            "${data.aws_s3_bucket.artifact_bucket.arn}/*"
          ]
        },
        {
          Action = [
            "ecr:GetAuthorizationToken",
          ]
          Effect   = "Allow"
          Resource = "*"
        },
        {
          Action = [
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "logs:CreateLogGroup"
          ]
          Effect = "Allow"
          # TODO: determine if we should move this to a per-service basis
          Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:*"
        },
      ]
    })
  }

}


resource "aws_vpc" "env_vpc" {
  cidr_block = "10.0.0.0/16"

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.launchflow_project}-${var.launchflow_environment}-vpc"
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.env_vpc.id
}

resource "aws_subnet" "public" {
  for_each                = { for az in local.az_names : az => az if substr(local.subnet_blocks["${az}-public"], 0, 1) != "" }
  vpc_id                  = aws_vpc.env_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.env_vpc.cidr_block, 8, index(data.aws_availability_zones.available.names, each.value) * 2)
  availability_zone       = each.value
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.launchflow_project}-${var.launchflow_environment}-${each.value}-public-subnet"
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
    Public      = "true"
  }
}


resource "aws_subnet" "private" {
  for_each          = { for az in local.az_names : az => az if substr(local.subnet_blocks["${az}-private"], 0, 1) != "" }
  vpc_id            = aws_vpc.env_vpc.id
  cidr_block        = cidrsubnet(aws_vpc.env_vpc.cidr_block, 8, index(data.aws_availability_zones.available.names, each.value) * 2 + 1)
  availability_zone = each.value

  tags = {
    Name        = "${var.launchflow_project}-${var.launchflow_environment}-${each.value}-private-subnet"
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
    Public      = "false"
  }
}

resource "aws_route_table" "public_route_table" {
  vpc_id = aws_vpc.env_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name        = "${var.launchflow_project}-${var.launchflow_environment}-public-route-table"
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
    Public      = "true"
  }
}


resource "aws_route_table_association" "route_table_association" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public_route_table.id
}

resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.env_vpc.id

  tags = {
    Name        = "${var.launchflow_project}-${var.launchflow_environment}-private-route-table"
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
    Public      = "false"
  }
}

resource "aws_route_table_association" "private" {
  for_each       = aws_subnet.private
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private_route_table.id
}


output "vpc_id" {
  value = aws_vpc.env_vpc.id
}

output "role_arn" {
  value = aws_iam_role.env_role.arn
}
