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

resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_zone" "primary" {
  name = var.domain_name
}

resource "aws_route53_record" "dns_records" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.primary.zone_id
}

resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.dns_records : record.fqdn]
}


output "domain_name" {
  value = aws_acm_certificate.cert.domain_name
}

output "aws_arn" {
  value = aws_acm_certificate.cert.arn
}
