provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = var.launchflow_project
      Environment = var.launchflow_environment
    }
  }
}

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-ebs"]
  }
}

data "aws_subnets" "lf_vpc_subnets" {
  filter {
    name   = "vpc-id"
    values = [var.vpc_id]
  }
  tags = {
    "Project" : var.launchflow_project,
    "Environment" : var.launchflow_environment
    # NOTE: We use public subnets so we can install docker at startup. The instances
    # should not be accessible to the internet when associate_public_ip_address is set
    # to false on the instance.
    "Public" : "true"
  }
}

data "aws_security_group" "default_vpc_sg" {
  vpc_id = var.vpc_id
  name   = "default"
}

resource "aws_security_group" "docker_sg" {
  name        = "${var.resource_id}-docker-sg"
  description = "Allow inbound traffic"
  vpc_id      = var.vpc_id

  dynamic "ingress" {
    for_each = var.firewall_cfg.expose_ports

    content {
      from_port = ingress.value
      to_port   = ingress.value
      protocol  = "tcp"
      # We only allow traffic outside the VPC if the instance is publicly accessible
      cidr_blocks     = var.publicly_accessible ? ["0.0.0.0/0"] : []
      security_groups = [data.aws_security_group.default_vpc_sg.id]
    }
  }

  # ssh access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

locals {
  sorted_subnets = sort(data.aws_subnets.lf_vpc_subnets.ids)
}


resource "tls_private_key" "rsa_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "${var.resource_id}-key"
  public_key = tls_private_key.rsa_key.public_key_openssh
}


resource "aws_instance" "docker_host" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = var.instance_type
  subnet_id                   = local.sorted_subnets[0]
  key_name                    = aws_key_pair.generated_key.key_name
  associate_public_ip_address = var.associate_public_ip_address

  root_block_device {
    volume_size = var.disk_size_gb
  }

  user_data = <<EOF
#!/bin/bash
sudo yum update -y
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user
ENV_VAR_FLAGS="${join(" ", [for k, v in var.docker_cfg.environment_variables : format("-e %s=%s", k, v)])}"
PORTS="${join(" ", [for port in var.firewall_cfg.expose_ports : format("-p %s:%s", port, port)])}"
docker run --name ${var.resource_id} -d $${PORTS} $${ENV_VAR_FLAGS} ${var.docker_cfg.image} ${join(" ", var.docker_cfg.args)}
EOF

  vpc_security_group_ids = [
    aws_security_group.docker_sg.id
  ]

  tags = {
    Project     = var.launchflow_project
    Environment = var.launchflow_environment
    Name        = "${var.resource_id}-${var.launchflow_environment}"
  }

  monitoring              = true
  disable_api_termination = false
  ebs_optimized           = true
}


output "private_key" {
  value     = tls_private_key.rsa_key.private_key_pem
  sensitive = true
}

output "public_ip" {
  value = aws_instance.docker_host.public_ip
}

output "private_ip" {
  value = aws_instance.docker_host.private_ip
}

output "ports" {
  value = var.firewall_cfg.expose_ports
}

output "additional_outputs" {
  value = var.additional_outputs
}

output "aws_arn" {
  value = aws_instance.docker_host.arn
}
