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

resource "aws_lambda_function_url" "default" {
  function_name      = var.function_arn
  qualifier          = var.function_alias
  authorization_type = var.authorization

  dynamic "cors" {
    for_each = var.cors != null ? [var.cors] : []
    content {
      allow_credentials = cors.value.allow_credentials
      allow_origins     = cors.value.allow_origins
      allow_methods     = cors.value.allow_methods
      allow_headers     = cors.value.allow_headers
      expose_headers    = cors.value.expose_headers
      max_age           = cors.value.max_age
    }
  }  
}


output "function_url" {
  value = aws_lambda_function_url.default.function_url
}

output "url_id" {
  value = aws_lambda_function_url.default.id
}

output "aws_arn" {
  value = "TODO"
}
