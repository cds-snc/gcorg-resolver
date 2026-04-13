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
