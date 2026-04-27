# Public hosted zone for gcorgs.cdssandbox.xyz

# The parent zone (cdssandbox.xyz) is managed by CDS SRE. The subdomain
# is delegated via NS records.

resource "aws_route53_zone" "gcorgs" {
  name = "gcorgs.cdssandbox.xyz"
}


# Get the remote states for prod and dev

data "terraform_remote_state" "dev" {
  backend = "s3"
  config = {
    bucket = "gcorg-resolver-dev-tfstate-a7f3k9"
    key    = "lambda-api/terraform.tfstate"
    region = "ca-central-1"
  }
}


# Create an ACM certificate

resource "aws_acm_certificate" "dev" {
  domain_name = "dev.gcorgs.cdssandbox.xyz"
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

# Create Route 53 records for ACM DNS challenge

resource "aws_route53_record" "cert_validation_dev" {
  for_each = {
    for dvo in aws_acm_certificate.dev.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type 
    }
  }

  zone_id         = aws_route53_zone.gcorgs.zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.record]
  allow_overwrite = true
}


resource "aws_acm_certificate_validation" "dev" {
  certificate_arn         = aws_acm_certificate.dev.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_dev : record.fqdn]
}


resource "aws_apigatewayv2_domain_name" "dev" {
  domain_name = "dev.gcorgs.cdssandbox.xyz"

  domain_name_configuration {
    certificate_arn = aws_acm_certificate.dev.arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  depends_on = [aws_acm_certificate_validation.dev]
}

resource "aws_apigatewayv2_api_mapping" "dev" {
  api_id      = data.terraform_remote_state.dev.outputs.api_id
  domain_name = aws_apigatewayv2_domain_name.dev.id
  stage       = "$default"
}


# Now make the actual Route 53 record

resource "aws_route53_record" "dev" {
  zone_id = aws_route53_zone.gcorgs.zone_id
  name    = "dev.gcorgs.cdssandbox.xyz"
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.dev.domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.dev.domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = true
  }
}