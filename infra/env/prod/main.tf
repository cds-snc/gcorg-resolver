terraform {
  required_version = ">= 1.14"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  backend "s3" {
    bucket       = "gcorg-resolver-prod-tfstate-b8g2l4"
    key          = "prod/lambda-api/terraform.tfstate"
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

resource "random_password" "origin_verify" {
  length  = 48
  special = false
}

module "lambda_api" {
  source = "../../aws/lambda-api"

  env               = var.env
  lambda_zip_path   = "${path.root}/../../.build/lambda.zip"
  billing_tag_value = var.billing_tag_value

  origin_verify_secret = random_password.origin_verify.result
}
