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

resource "null_resource" "build_lambda_layer" {
  provisioner "local-exec" {
    command = <<EOT
      set -e
      mkdir -p python
      pip install --target=./python ${join(" ", var.packages)}
      zip -r layer.zip python
    EOT
  }
}

resource "aws_lambda_layer_version" "python_packages" {
  filename   = "${path.module}/layer.zip"
  layer_name = var.resource_id
}


output "aws_arn" {
  value = aws_lambda_layer_version.python_packages.arn
}
