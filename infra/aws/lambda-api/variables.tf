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
