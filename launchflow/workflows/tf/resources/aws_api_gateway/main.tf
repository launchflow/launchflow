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


resource "aws_apigatewayv2_api" "default" {
  name          = "${var.resource_id}-gateway"
  protocol_type = "HTTP"
}

# NOTE: we will always use default since we provision 1 api gatway per env
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.default.id
  name        = "$default"
  auto_deploy = true
}


output "api_gateway_id" {
  value = aws_apigatewayv2_api.default.id
}

output "api_gateway_endpoint" {
  value = aws_apigatewayv2_api.default.api_endpoint
}

output "aws_arn" {
  value = aws_apigatewayv2_api.default.arn
}
