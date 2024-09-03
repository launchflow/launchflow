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


resource "aws_lambda_event_source_mapping" "default" {
  event_source_arn = var.event_source_arn
  function_name    = var.function_arn
  batch_size       = var.batch_size
}


output "aws_arn" {
  value = aws_lambda_event_source_mapping.default.arn
}
