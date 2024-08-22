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


resource "aws_security_group" "alb_sg" {
  vpc_id                 = var.vpc_id
  name                   = "${var.resource_id}-alb-sg"
  description            = "Security group for alb"
  revoke_rules_on_delete = true
}

resource "aws_security_group_rule" "alb_http_ingress" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "TCP"
  description       = "Allow http inbound traffic from internet"
  security_group_id = aws_security_group.alb_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_https_ingress" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "TCP"
  description       = "Allow https inbound traffic from internet"
  security_group_id = aws_security_group.alb_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  description       = "Allow outbound traffic from alb"
  security_group_id = aws_security_group.alb_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

# Create the Application Load Balancer
resource "aws_alb" "application_load_balancer" {
  name               = var.resource_id
  internal           = false
  load_balancer_type = "application"
  subnets            = data.aws_subnets.lf_public_vpc_subnets.ids
  security_groups    = [aws_security_group.alb_sg.id]

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
  }
}

#Defining the target group and a health check on the application
resource "aws_lb_target_group" "target_group" {
  name        = var.resource_id
  port        = var.container_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  # TODO: Expose more options for health checking
  dynamic "health_check" {
    for_each = var.health_check_path != null ? [var.health_check_path] : []
    content {
      path                = health_check.value
      protocol            = "HTTP"
      matcher             = "200"
      port                = "traffic-port"
      healthy_threshold   = 2
      unhealthy_threshold = 2
      timeout             = 10
      interval            = 30
    }
  }
}

data "aws_acm_certificate" "issued" {
  count  = var.domain_name != null ? 1 : 0
  domain = var.domain_name
}

data "aws_route53_zone" "selected" {
  count = var.domain_name != null ? 1 : 0
  name  = var.domain_name
}

#Defines an ALB listener
resource "aws_lb_listener" "listener" {
  load_balancer_arn = aws_alb.application_load_balancer.arn
  port              = var.domain_name != null ? 443 : 80
  protocol          = var.domain_name != null ? "HTTPS" : "HTTP"
  ssl_policy        = var.domain_name != null ? "ELBSecurityPolicy-2016-08" : null
  certificate_arn   = var.domain_name != null ? data.aws_acm_certificate.issued[0].arn : null

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.target_group.arn
  }
}


resource "aws_route53_record" "alias_route53_record" {
  count = var.domain_name != null ? 1 : 0

  zone_id = data.aws_route53_zone.selected[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_alb.application_load_balancer.dns_name
    zone_id                = aws_alb.application_load_balancer.zone_id
    evaluate_target_health = true
  }
}



output "alb_target_group_arn" {
  value = aws_lb_target_group.target_group.arn
}

output "alb_security_group_id" {
  value = aws_security_group.alb_sg.id
}

output "alb_dns_name" {
  value = aws_alb.application_load_balancer.dns_name
}

output "aws_arn" {
  value = aws_alb.application_load_balancer.arn
}
