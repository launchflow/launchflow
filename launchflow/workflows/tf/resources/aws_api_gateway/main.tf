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
  name          = var.resource_id
  protocol_type = var.protocol_type

  dynamic "cors_configuration" {
    for_each = var.cors != null ? [var.cors] : []
    content {
      allow_credentials = cors_configuration.value.allow_credentials
      allow_headers     = cors_configuration.value.allow_headers
      allow_methods     = cors_configuration.value.allow_methods
      allow_origins     = cors_configuration.value.allow_origins
      expose_headers    = cors_configuration.value.expose_headers
      max_age           = cors_configuration.value.max_age
    }
  }
}


# NOTE: we will always use default since we provision 1 api gateway per env
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
