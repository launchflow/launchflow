provider "aws" {
  allowed_account_ids = [var.aws_account_id]
  region              = var.aws_region
}

resource "aws_s3_bucket" "s3_bucket" {
  bucket = var.resource_id
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment
  }
  force_destroy = var.force_destroy
}

resource "aws_iam_policy" "policy" {
  name = "${var.resource_id}-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:*",
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.s3_bucket.arn}",
          "${aws_s3_bucket.s3_bucket.arn}/*"
        ]
      },
    ]
  })
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment
  }
}

resource "aws_iam_role_policy_attachment" "policy_attach" {
  role       = var.env_role_name
  policy_arn = aws_iam_policy.policy.arn
}

output "bucket_name" {
  value = aws_s3_bucket.s3_bucket.bucket
}

output "aws_arn" {
  value = aws_s3_bucket.s3_bucket.arn
}
