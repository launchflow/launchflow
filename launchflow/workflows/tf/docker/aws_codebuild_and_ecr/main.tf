provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region     = var.aws_region
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
  name = var.launchflow_env_role_name
}


# Create an ECR repository for the given service
resource "aws_ecr_repository" "service_repo" {
  name                 = "${var.service_name}-${var.launchflow_project}-${var.launchflow_environment}"
  image_tag_mutability = "MUTABLE"

  force_delete = true

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

data "aws_iam_policy_document" "ecr_policy_doc" {
  statement {
    sid    = "AllowCodeBuild"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [
        data.aws_iam_role.launchflow_env_role.arn
      ]
    }

    actions = [
      "ecr:*"
    ]
  }
}

resource "aws_ecr_repository_policy" "ecr_policy" {
  repository = aws_ecr_repository.service_repo.name
  policy     = data.aws_iam_policy_document.ecr_policy_doc.json
}



# CodeBuild project
resource "aws_codebuild_project" "service_build" {

  name          = "${var.service_name}-${var.launchflow_project}-${var.launchflow_environment}-build"
  description   = "CodeBuild project for ${var.service_name} service"
  build_timeout = "30"
  service_role  = data.aws_iam_role.launchflow_env_role.arn

  artifacts {
    type = "NO_ARTIFACTS"
  }

  cache {
    type     = "S3"
    location = "${data.aws_s3_bucket.build_artifacts.bucket}/builds/cache"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:7.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = var.aws_region
    }
    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = var.aws_account_id
    }
    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.service_repo.name
    }
    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }
    environment_variable {
      name  = "SOURCE_TAR_NAME"
      value = "source.tar.gz"
    }
  }

  lifecycle {
    ignore_changes = [
      logs_config[0].cloudwatch_logs
    ]
  }

  logs_config {
    cloudwatch_logs {
      status = "DISABLED"
    }

    s3_logs {
      status   = "ENABLED"
      location = "${data.aws_s3_bucket.build_artifacts.bucket}/builds/log"
    }
  }

  source {
    type      = "S3"
    buildspec = file("${path.module}/buildspec.yml")
    location  = "${data.aws_s3_bucket.build_artifacts.bucket}/${var.source_path}/"
  }

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }

}

output "docker_repository" {
  value = aws_ecr_repository.service_repo.repository_url
}


output "codebuild_project_name" {
  value = aws_codebuild_project.service_build.name
}
