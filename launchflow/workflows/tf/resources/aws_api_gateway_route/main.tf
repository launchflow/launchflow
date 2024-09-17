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


resource "aws_apigatewayv2_route" "default" {
  api_id    = var.api_gateway_id
  route_key = var.route_key
  target    = var.api_integration_id != null ? "integrations/${var.api_integration_id}" : null
}


output "api_route_id" {
  value = aws_apigatewayv2_route.default.id
}

output "aws_arn" {
  value = "TODO"
}
