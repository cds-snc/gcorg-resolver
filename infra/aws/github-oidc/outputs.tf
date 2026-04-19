output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}

output "role_arns" {
  description = "Map of role name → ARN for each role created."
  value       = { for name, role in aws_iam_role.this : name => role.arn }
}
