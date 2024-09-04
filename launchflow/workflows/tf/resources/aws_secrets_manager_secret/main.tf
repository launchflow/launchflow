provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region              = var.aws_region
}

resource "aws_secretsmanager_secret" "secret" {
  name                    = var.resource_id
  recovery_window_in_days = var.recovery_window_in_days
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment
  }
}

# Import the launchflow environment role
data "aws_iam_role" "launchflow_env_role" {
  name = var.env_role_name
}


data "aws_iam_policy_document" "secret_policy_data" {
  statement {
    sid    = "AllowEnvironmentRole"
    effect = "Allow"

    principals {
      type = "AWS"
      identifiers = [
        data.aws_iam_role.launchflow_env_role.arn
      ]
    }

    actions   = ["secretsmanager:*"]
    resources = [aws_secretsmanager_secret.secret.arn]
  }
}

resource "aws_secretsmanager_secret_policy" "secret_policy" {
  secret_arn = aws_secretsmanager_secret.secret.arn
  policy     = data.aws_iam_policy_document.secret_policy_data.json
}


output "secret_id" {
  value = aws_secretsmanager_secret.secret.id
}


output "aws_arn" {
  value = aws_secretsmanager_secret.secret.arn
}
