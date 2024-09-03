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
    "Environment" : var.launchflow_environment
    "Public" : var.publicly_accessible ? "true" : "false"
  }
}

data "aws_subnet" "details" {
  for_each = toset(data.aws_subnets.lf_vpc_subnets.ids)
  id       = each.value
}

data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}

resource "aws_db_subnet_group" "default" {
  name        = "${var.resource_id}-subnet-group"
  subnet_ids  = data.aws_subnets.lf_vpc_subnets.ids
  description = "Subnet group for ${var.resource_id}"
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.resource_id}-rds-sg"
  description = "Security group for ${var.resource_id} - ${var.publicly_accessible ? "Allow inbound traffic" : "Only VPC inbound traffic"}"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.engine == "postgres" ? 5432 : 3306
    to_port         = var.engine == "postgres" ? 5432 : 3306
    protocol        = "tcp"
    cidr_blocks     = var.publicly_accessible ? ["0.0.0.0/0"] : []
    security_groups = [data.aws_security_group.default_vpc_sg.id]
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

# The default parameter group does not allow setting rds.force_ssl parameter for MySQL
resource "aws_db_parameter_group" "params" {
  name   = "${var.resource_id}-parameter-group"
  family = var.engine_family

  dynamic "parameter" {
    for_each = var.engine == "postgres" ? ["rds.force_ssl"] : []
    content {
      apply_method = "immediate"
      name         = parameter.value
      value        = "0"
    }
  }
}

resource "random_password" "user-password" {
  length  = 16
  special = false
}

resource "aws_db_instance" "default" {
  identifier_prefix      = substr(var.resource_id, 0, 30)
  allocated_storage      = var.allocated_storage_gb
  db_name                = var.database_name
  engine                 = var.engine
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  parameter_group_name   = aws_db_parameter_group.params.name
  username               = "${var.database_name}User"
  password               = random_password.user-password.result
  skip_final_snapshot    = true
  publicly_accessible    = var.publicly_accessible
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  multi_az               = var.highly_available
  db_subnet_group_name   = aws_db_subnet_group.default.name

  # TODO: Add monitoring options
}


locals {
  endpoint = aws_db_instance.default.endpoint
  username = aws_db_instance.default.username
  password = aws_db_instance.default.password
  port     = aws_db_instance.default.port
  dbname   = aws_db_instance.default.db_name
  aws_arn  = aws_db_instance.default.arn
}


output "endpoint" {
  value = local.endpoint
}

output "username" {
  value = local.username
}

output "password" {
  value     = local.password
  sensitive = true
}

output "port" {
  value = local.port
}

output "dbname" {
  value = local.dbname
}

output "region" {
  value = var.aws_region
}

output "aws_arn" {
  value = local.aws_arn
}
