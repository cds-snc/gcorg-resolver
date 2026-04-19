output "plan_role_arn" {
  description = "ARN of the role assumed by the terraform-plan workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-plan"]
}

output "apply_role_arn" {
  description = "ARN of the role assumed by the terraform-apply workflow."
  value       = module.github_oidc.role_arns["gcorg-resolver-apply"]
}

output "oidc_provider_arn" {
  value = module.github_oidc.oidc_provider_arn
}
