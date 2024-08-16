provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region              = var.aws_region
}

# Import the artifact_bucket
data "aws_s3_bucket" "build_artifacts" {
  bucket = var.artifact_bucket
}


resource "aws_iam_role" "launchflow_releaser_role" {
  name = "${var.resource_id}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.launchflow_cloud_aws_account_id}:role/${var.launchflow_cloud_role_name}"
        }
        Condition = {
          StringEquals = {
            "sts:ExternalId" = var.launchflow_cloud_external_role_id
          }
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      },
    ]
  })
}

# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}


resource "aws_iam_policy" "launchflow_releaser_policy" {
  name = "${var.resource_id}-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = var.environment_allowed_actions,
        Resource = "*",
        Condition = {
          "StringEquals" = {
            "aws:ResourceTag/Environment" = var.launchflow_environment
            "aws:ResourceTag/Project"     = var.launchflow_project
          }
        }
        }, {
        Effect   = "Allow"
        Action   = var.account_allowed_actions,
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = var.environment_allowed_actions,
        Resource = "*",
        Condition = {
          "StringEquals" = {
            "aws:RequestTag/Environment" = var.launchflow_environment
            "aws:RequestTag/Project"     = var.launchflow_project
          },
        }
      },
      {
        Action = [
          "s3:*",
        ]
        Effect = "Allow"
        Resource = [
          data.aws_s3_bucket.build_artifacts.arn,
          "${data.aws_s3_bucket.build_artifacts.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/aws/codebuild/${var.resource_id}:*"
      },
      {
        Action = [
          "iam:PassRole"
        ]
        Effect = "Allow"
        Resource = [
          data.aws_iam_role.launchflow_env_role.arn
        ]
      }

    ]
  })
}

resource "aws_iam_role_policy_attachment" "launchflow_releaser_policy_attachment" {
  role       = aws_iam_role.launchflow_releaser_role.name
  policy_arn = aws_iam_policy.launchflow_releaser_policy.arn
}

# CodeBuild project
resource "aws_codebuild_project" "project" {

  name          = var.resource_id
  description   = "CodeBuild project: ${var.resource_id}"
  build_timeout = 60
  service_role  = aws_iam_role.launchflow_releaser_role.arn

  # TODO: make this configurable
  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true
    type                        = "LINUX_CONTAINER"

    # Default environment variables
    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = var.aws_account_id
    }
  }

  logs_config {
    cloudwatch_logs {
      status = "ENABLED"
    }
  }

  source {
    type      = "S3"
    buildspec = file("${path.module}/buildspec.yml")
    location  = "${data.aws_s3_bucket.build_artifacts.bucket}/"
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

output "code_build_project_arn" {
  value = aws_codebuild_project.project.arn
}

output "releaser_role_arn" {
  value = aws_iam_role.launchflow_releaser_role.arn
}
