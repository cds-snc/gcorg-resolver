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

data "terraform_remote_state" "prod" {
  backend = "s3"
  config = {
    bucket = "gcorg-resolver-prod-tfstate-b8g2l4"
    key    = "prod/lambda-api/terraform.tfstate"
    region = "ca-central-1"
  }
}


# Create an ACM certificate (us-east-1, required by CloudFront)

resource "aws_acm_certificate" "dev" {
  provider          = aws.us_east_1
  domain_name       = "dev.gcorgs.cdssandbox.xyz"
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
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.dev.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_dev : record.fqdn]
}


# CloudFront distribution with geo-restriction (CA + US only)

resource "aws_cloudfront_distribution" "dev" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "gcorg-resolver dev"
  aliases         = ["dev.gcorgs.cdssandbox.xyz"]
  price_class     = "PriceClass_100" # NA + EU edges (cheapest tier that includes CA + US)

  origin {
    domain_name = trimprefix(data.terraform_remote_state.dev.outputs.api_endpoint, "https://")
    origin_id   = "api-gateway-dev"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "api-gateway-dev"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    # AWS-managed policies:
    # CachingDisabled - API responses are dynamic
    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    # AllViewerExceptHostHeader - forwards everything except Host (which CloudFront sets to origin)
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["CA", "US"]
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.dev.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  depends_on = [aws_acm_certificate_validation.dev]
}


# Route 53 alias to CloudFront

resource "aws_route53_record" "dev" {
  zone_id = aws_route53_zone.gcorgs.zone_id
  name    = "dev.gcorgs.cdssandbox.xyz"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.dev.domain_name
    zone_id                = aws_cloudfront_distribution.dev.hosted_zone_id
    evaluate_target_health = false
  }
}


# Prod: apex domain

resource "aws_acm_certificate" "prod" {
  provider          = aws.us_east_1
  domain_name       = "gcorgs.cdssandbox.xyz"
  validation_method = "DNS"
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "cert_validation_prod" {
  for_each = {
    for dvo in aws_acm_certificate.prod.domain_validation_options : dvo.domain_name => {
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

resource "aws_acm_certificate_validation" "prod" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.prod.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation_prod : record.fqdn]
}

resource "aws_cloudfront_distribution" "prod" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "gcorg-resolver prod"
  aliases         = ["gcorgs.cdssandbox.xyz"]
  price_class     = "PriceClass_100"

  origin {
    domain_name = trimprefix(data.terraform_remote_state.prod.outputs.api_endpoint, "https://")
    origin_id   = "api-gateway-prod"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "api-gateway-prod"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]

    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" # CachingDisabled
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac" # AllViewerExceptHostHeader
  }

  restrictions {
    geo_restriction {
      restriction_type = "whitelist"
      locations        = ["CA", "US"]
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.prod.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  depends_on = [aws_acm_certificate_validation.prod]
}

resource "aws_route53_record" "prod" {
  zone_id = aws_route53_zone.gcorgs.zone_id
  name    = "gcorgs.cdssandbox.xyz"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.prod.domain_name
    zone_id                = aws_cloudfront_distribution.prod.hosted_zone_id
    evaluate_target_health = false
  }
}