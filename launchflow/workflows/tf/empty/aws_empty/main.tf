provider "aws" {
  # AWS destroys cant read this from the state file for some reason...
  region = var.aws_region
}
