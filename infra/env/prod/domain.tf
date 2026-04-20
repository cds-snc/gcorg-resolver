locals {
  api_subdomain = "${var.subdomain}.${var.domain_name}"
}

resource "aws_acm_certificate" "api" {
  domain_name       = local.api_subdomain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn
}

resource "aws_apigatewayv2_domain_name" "api" {
  domain_name = local.api_subdomain

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.api.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  depends_on = [aws_acm_certificate_validation.api]
}

resource "aws_apigatewayv2_api_mapping" "api" {
  api_id      = module.lambda_api.api_id
  domain_name = aws_apigatewayv2_domain_name.api.id
  stage       = "$default"
}
