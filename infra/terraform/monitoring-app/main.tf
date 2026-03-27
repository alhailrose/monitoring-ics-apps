terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to store state in S3 (recommended for team)
  # backend "s3" {
  #   bucket  = "ics-ms-terraform-state"
  #   key     = "monitoring-app/terraform.tfstate"
  #   region  = "ap-southeast-3"
  #   profile = "sandbox-ms"
  # }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# ── Existing infrastructure (data sources) ────────────────────────────────────

data "aws_vpc" "ics_ms" {
  filter {
    name   = "tag:Name"
    values = ["vpc-ics-ms"]
  }
}

data "aws_subnet" "private_a" {
  filter {
    name   = "tag:Name"
    values = ["subnet-ics-ms-private-a"]
  }
}

data "aws_security_group" "private" {
  name   = "ics-ms-private-sg"
  vpc_id = data.aws_vpc.ics_ms.id
}

data "aws_security_group" "efs_client" {
  name   = "ics-ms-efs-client-sg"
  vpc_id = data.aws_vpc.ics_ms.id
}

# ── New SSH key pair ──────────────────────────────────────────────────────────
# Generate dulu di lokal: ssh-keygen -t ed25519 -f ~/.ssh/ics-ms-monitoringapps -C "ics-ms-monitoringapps"
# Lalu terraform apply akan upload public key ke AWS

resource "aws_key_pair" "monitoringapps" {
  key_name   = "ics-ms-monitoringapps"
  public_key = file(var.ssh_public_key_path)

  tags = {
    Name      = "ics-ms-monitoringapps"
    ManagedBy = "terraform"
  }
}

# Latest Ubuntu 22.04 LTS in ap-southeast-3
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
