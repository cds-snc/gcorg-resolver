output "api_id" {
  value = module.lambda_api.api_id
}

output "api_endpoint" {
  value = module.lambda_api.api_endpoint
}

output "function_name" {
  value = module.lambda_api.function_name
}

output "function_arn" {
  value = module.lambda_api.function_arn
}

output "origin_verify_secret" {
  description = "Read by the DNS stack's CloudFront distribution."
  value       = random_password.origin_verify.result
  sensitive   = true
}
