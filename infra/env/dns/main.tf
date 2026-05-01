terraform {
  required_version = ">= 1.14"

  required_providers {
      aws = {
        source = "hashicorp/aws"
        version = "~> 6.0"
      }
  }

  backend "s3" {
    bucket       = "gcorg-resolver-dev-tfstate-a7f3k9"
    key          = "dns/terraform.tfstate"
    region       = "ca-central-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      CostCentre = var.billing_tag_value
      Terraform  = true
    }
  }
}

# CloudFront requires ACM certificates in us-east-1.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = {
      CostCentre = var.billing_tag_value
      Terraform  = true
    }
  }
}