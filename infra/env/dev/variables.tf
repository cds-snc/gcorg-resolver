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
