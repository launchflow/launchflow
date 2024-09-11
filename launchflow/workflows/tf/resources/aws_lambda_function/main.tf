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

# Import the private subnets for the VPC
data "aws_subnets" "lf_private_vpc_subnets" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment,
    "Public" : "false"
  }
}

# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}

data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}



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
  memory_size   = var.memory_size_mb
  timeout       = var.timeout_seconds
  publish          = true

  # Conditionally assign filename and handler for ZIP package type
  filename         = var.package_type == "Zip" ? data.archive_file.lambda.output_path : null
  handler          = var.package_type == "Zip" ? "hello.lambda_handler" : null
  runtime          = var.package_type == "Zip" ? var.runtime : null
  source_code_hash = var.package_type == "Zip" ? data.archive_file.lambda.output_base64sha256 : null

  # Conditionally assign image_uri for Image package type
  image_uri        = var.package_type == "Image" ? var.image_uri : null

  # NOTE: We set this to speed up the destroy process. Without this, lambda can hold
  # onto the security group for ~30mins and block it from being deleted.
  replace_security_groups_on_destroy = true

  vpc_config {
    security_group_ids = [data.aws_security_group.default_vpc_sg.id]
    subnet_ids         = [data.aws_subnets.lf_private_vpc_subnets.ids[0]]
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


# TODO: Determine if we can remove this / restrict the scope a bit more
resource "aws_iam_role_policy_attachment" "iam_role_policy_attachment_lambda_vpc_access_execution" {
  role       = data.aws_iam_role.launchflow_env_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_alias" "lambda_alias" {
  name             = var.launchflow_environment
  function_name    = aws_lambda_function.default.arn
  function_version = aws_lambda_function.default.version

  lifecycle {
    ignore_changes = [
      function_version
    ]
  }
}


output "alias_name" {
  value = aws_lambda_alias.lambda_alias.name
}

output "function_name" {
  value = aws_lambda_function.default.function_name
}

output "aws_arn" {
  value = aws_lambda_function.default.arn
}
