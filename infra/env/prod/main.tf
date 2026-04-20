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
    key          = "prod/lambda-api/terraform.tfstate"
    region       = "ca-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      CostCentre = var.billing_tag_value
      Terraform  = true
    }
  }
}

module "lambda_api" {
  source = "../../aws/lambda-api"

  env             = var.env
  lambda_zip_path = "${path.root}/../../.build/lambda.zip"
}
