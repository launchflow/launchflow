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

data "aws_subnets" "lf_vpc_subnets" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment,
    "Public" : false
  }
}


resource "aws_vpc_endpoint" "default" {
  service_name      = var.service_name
  vpc_endpoint_type = var.endpoint_type
  vpc_id            = var.vpc_id

  subnet_ids          = var.endpoint_type == "Interface" ? data.aws_subnets.lf_vpc_subnets.ids : []
  private_dns_enabled = var.endpoint_type == "Interface"
}

output "aws_arn" {
  value = aws_vpc_endpoint.default.arn
}
