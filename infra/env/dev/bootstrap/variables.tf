variable "billing_tag_value" {
  description = "The value used to track billing."
  type        = string
}

variable "env" {
  description = "The current running environment."
  type        = string
}

variable "region" {
  description = "The region to build infrastructure in."
  type        = string
}

variable "github_org" {
  description = "GitHub organization or user that owns the repo."
  type        = string
}

variable "github_repo" {
  description = "GitHub repo name (without org prefix)."
  type        = string
}

variable "state_bucket_dev" {
  description = "Name of the S3 bucket holding Terraform state for the dev app stack."
  type        = string
}

variable "state_bucket_prod" {
  description = "Name of the S3 bucket holding Terraform state for the prod app stack."
  type        = string
}
