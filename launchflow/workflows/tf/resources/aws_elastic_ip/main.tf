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


resource "aws_eip" "eip" {
  domain = var.domain
  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

output "allocation_id" {
  value = aws_eip.eip.allocation_id
}

output "public_ip" {
  value = aws_eip.eip.public_ip
}

output "private_ip" {
  value = aws_eip.eip.private_ip
}

output "aws_arn" {
  value = "TODO"
}
