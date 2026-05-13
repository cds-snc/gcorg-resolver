variable "env" {
  description = "The current running environment."
  type        = string
}

variable "function_name" {
  type    = string
  default = null
}

variable "lambda_zip_path" {
  type        = string
  description = "Path to the pre-built Lambda deployment zip"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "lambda_max_concurrency" {
  description = "Maximum concurrent Lambda executions."
  type        = number
  default     = 25
}

variable "api_throttle_rate" {
  description = "Sustained requests per second across all routes."
  type        = number
  default     = 50
}

variable "api_throttle_burst" {
  description = "Maximum burst of concurrent requests before throttling kicks in."
  type        = number
  default     = 100
}

variable "billing_tag_value" {
  description = "The value used to track billing costs."
  type        = string
}
