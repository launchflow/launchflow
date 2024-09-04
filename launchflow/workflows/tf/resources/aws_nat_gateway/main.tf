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

data "aws_route_table" "private_route_table" {
  count = var.private_route_config != null ? 1 : 0

  vpc_id = var.vpc_id

  tags = {
    "Project"     = var.launchflow_project
    "Environment" = var.launchflow_environment
    "Public"      = "false"
  }
}


resource "aws_nat_gateway" "nat_gateway" {
  allocation_id = var.eip_allocation_id
  subnet_id     = data.aws_subnets.lf_public_vpc_subnets.ids[0]

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

resource "aws_route" "route" {
  count = var.private_route_config != null ? 1 : 0

  route_table_id         = data.aws_route_table.private_route_table[0].id
  nat_gateway_id         = aws_nat_gateway.nat_gateway.id
  destination_cidr_block = var.private_route_config.destination_cidr_block
}


output "nat_gateway_id" {
  value = aws_nat_gateway.nat_gateway.id
}

output "aws_arn" {
  value = "TODO"
}
