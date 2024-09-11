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


data "aws_apigatewayv2_api" "imported_api_gateway" {
  api_id = var.api_gateway_id
}


resource "aws_apigatewayv2_integration" "default" {
  api_id           = var.api_gateway_id
  integration_type = "AWS_PROXY"
  integration_uri  = "${var.function_arn}:${var.function_alias}"
}

resource "aws_lambda_permission" "default" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.function_arn
  qualifier     = var.function_alias
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${data.aws_apigatewayv2_api.imported_api_gateway.execution_arn}/*/*"
}


output "api_integration_id" {
  value = aws_apigatewayv2_integration.default.id
}

output "aws_arn" {
  value = "TODO"
}
