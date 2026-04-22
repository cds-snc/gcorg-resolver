terraform {
  required_version = ">= 1.14"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "gcorg-resolver-dev-tfstate"
    key          = "bootstrap/terraform.tfstate"
    region       = "ca-central-1"
    encrypt      = true
    use_lockfile = true
  }
}
data "aws_caller_identity" "current" {}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      CostCentre = var.billing_tag_value
      Terraform  = true
    }
  }
}
