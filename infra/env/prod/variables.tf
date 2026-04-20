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

variable "domain_name" {
  description = "The root domain name (managed separately in Cloudflare)"
  type        = string
}

variable "subdomain" {
  description = "The subdomain to serve the API on (e.g. 'gcorgs' → gcorgs.<domain_name>)."
  type        = string
}
