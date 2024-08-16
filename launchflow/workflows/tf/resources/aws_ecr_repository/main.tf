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


# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}


# Create an ECR repository for the given service
resource "aws_ecr_repository" "repo" {
  name                 = var.resource_id
  image_tag_mutability = var.image_tag_mutability

  force_delete = var.force_delete

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

data "aws_iam_policy_document" "ecr_policy_doc" {
  statement {
    sid    = "AllowEnvironmentRole"
    effect = "Allow"

    principals {
      type = "AWS"
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
  repository = aws_ecr_repository.repo.name
  policy     = data.aws_iam_policy_document.ecr_policy_doc.json
}


output "repository_url" {
  value = aws_ecr_repository.repo.repository_url
}

output "aws_arn" {
  value = aws_ecr_repository.repo.arn
}
