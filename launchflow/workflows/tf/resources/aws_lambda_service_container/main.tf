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

# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}

# Define a Security Group for the ECS Tasks
resource "aws_security_group" "lambda_sg" {
  name        = "${var.resource_id}-lambda-sg"
  description = "Allow inbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.port
    to_port     = var.port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

# TODO: Determine if we should drop this rule since we already allow all VPC traffic
resource "aws_security_group_rule" "ecs_alb_ingress" {
    count                       = var.alb_security_group_id != null ? 1 : 0
    type                        = "ingress"
    from_port                   = 0
    to_port                     = 0
    protocol                    = "-1"
    description                 = "Allow inbound traffic from ALB"
    security_group_id           = aws_security_group.lambda_sg.id
    source_security_group_id    = var.alb_security_group_id
}

data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}

# JUST ADDED



resource "local_file" "hello" {
  content  = <<EOF
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/plain'
        },
        'body': 'Hello, World!'
    }

EOF
  filename = "${path.module}/hello.py"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_file = local_file.hello.filename
  output_path = "${path.module}/lambda.zip"
}


resource "aws_lambda_function" "default" {
  function_name = var.resource_id
  role          = data.aws_iam_role.launchflow_env_role.arn
  package_type  = var.package_type
  memory_size   = var.memory_size
  timeout       = var.timeout

  filename = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  handler = "hello.lambda_handler"
  runtime = "python3.11"

  vpc_config {
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids         = data.aws_subnets.lf_public_vpc_subnets.ids
  }

  environment {
    variables = {
      LAUNCHFLOW_PROJECT     = var.launchflow_project
      LAUNCHFLOW_ENVIRONMENT = var.launchflow_environment
    }
  }

  lifecycle {
    ignore_changes = [
      filename, image_config, image_uri
    ]
  }
}

# PULLED IN


resource "aws_apigatewayv2_api" "default" {
  name          = "${var.resource_id}-gateway"
  protocol_type = "HTTP"
}

resource "aws_lambda_permission" "default" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.default.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.default.execution_arn}/*/*"
}

resource "aws_apigatewayv2_integration" "default" {
  api_id           = aws_apigatewayv2_api.default.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.default.arn
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.default.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.default.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.default.id
  name        = "$default"
  auto_deploy = true
}


# Load Balancer setup


output "lambda_url" {
  description = "API Gateway URL for the Lambda Function"
  value       = aws_apigatewayv2_api.default.api_endpoint
}

output "aws_arn" {
  description = "Lambda Function ARN"
  value       = aws_lambda_function.default.arn
}