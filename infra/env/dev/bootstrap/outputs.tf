output "plan_role_arn_dev" {
  description = "ARN of the role assumed by the terraform-plan-dev workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-plan-dev"]
}

output "apply_role_arn_dev" {
  description = "ARN of the role assumed by the terraform-apply-dev workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-apply-dev"]
}

output "plan_role_arn_prod" {
  description = "ARN of the role assumed by the terraform-plan-prod workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-plan-prod"]
}

output "apply_role_arn_prod" {
  description = "ARN of the role assumed by the terraform-apply-prod workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-apply-prod"]
}

output "oidc_provider_arn" {
  value = module.github_oidc.oidc_provider_arn
}
