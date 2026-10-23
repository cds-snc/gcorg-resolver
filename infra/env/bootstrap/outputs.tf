output "plan_role_arn_prod" {
  description = "ARN of the role assumed by the terraform-plan-prod workflow."
  value       = module.github_oidc.roles["gcorg-resolver-plan-prod"].arn
}

output "apply_role_arn_prod" {
  description = "ARN of the role assumed by the terraform-apply-prod workflow."
  value       = module.github_oidc.roles["gcorg-resolver-apply-prod"].arn
}

# The upstream module doesn't output the provider ARN, which is fixed per account
output "oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider in this account."
  value       = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}
