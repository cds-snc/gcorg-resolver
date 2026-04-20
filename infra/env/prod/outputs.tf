output "api_endpoint" {
  value = module.lambda_api.api_endpoint
}

output "function_name" {
  value = module.lambda_api.function_name
}

output "function_arn" {
  value = module.lambda_api.function_arn
}

# After applying, use these values to create two DNS records in Cloudflare.
output "acm_validation_record" {
  description = "CNAME record so ACM can validate the certificate."
  value = {
    name  = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_name
    value = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_value
  }
}

output "custom_domain_cname" {
  description = "CNAME record to add in Cloudflare to route gcorgs.<domain> to API Gateway."
  value = {
    name  = var.subdomain
    value = aws_apigatewayv2_domain_name.api.domain_name_configuration[0].target_domain_name
  }
}
