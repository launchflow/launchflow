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

# Import the artifact_bucket
data "aws_s3_bucket" "build_artifacts" {
  bucket = var.artifact_bucket
}


# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}

# CodeBuild project
resource "aws_codebuild_project" "project" {

  name          = var.resource_id
  description   = "CodeBuild project: ${var.resource_id}"
  build_timeout = var.build_timeout_minutes
  service_role  = data.aws_iam_role.launchflow_env_role.arn

  # TODO: make this configurable
  artifacts {
    type = "NO_ARTIFACTS"
  }

  dynamic "cache" {
    for_each = var.cache != null ? [1] : []
    content {
      type     = var.cache.type
      location = var.cache.location
      modes    = var.cache.modes
    }
  }

  environment {
    compute_type                = var.environment.compute_type
    image                       = var.environment.image
    image_pull_credentials_type = var.environment.image_pull_credentials_type
    privileged_mode             = var.environment.privileged_mode
    type                        = var.environment.type

    # Default environment variables
    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = var.aws_account_id
    }
    # User-defined environment variables
    dynamic "environment_variable" {
      for_each = var.environment.environment_variables != null ? var.environment.environment_variables : []
      content {
        name  = environment_variable.value.name
        value = environment_variable.value.value
      }
    }
  }

  dynamic "logs_config" {
    for_each = var.logs_config != null ? [1] : []
    content {
      dynamic "cloudwatch_logs" {
        for_each = var.logs_config.cloud_watch_logs != null ? [1] : []
        content {
          status = var.logs_config.cloud_watch_logs.status
        }
      }
      dynamic "s3_logs" {
        for_each = var.logs_config.s3_logs != null ? [1] : []
        content {
          status   = var.logs_config.s3_logs.status
          location = var.logs_config.s3_logs.location
        }
      }
    }
  }

  source {
    type      = var.build_source.type
    buildspec = var.build_source.buildspec_path != null ? file(var.build_source.buildspec_path) : null
    location  = var.build_source.location
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

output "project_name" {
  value = aws_codebuild_project.project.name
}

output "aws_arn" {
  value = aws_codebuild_project.project.arn
}
