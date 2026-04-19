variable "account_id" {
  description = "The account ID to perform actions on."
  type        = string
}

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

variable "state_bucket" {
  description = "Name of the S3 bucket holding Terraform state for the app stack."
  type        = string
}
