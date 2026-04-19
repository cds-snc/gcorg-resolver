variable "github_org" {
  description = "GitHub organization or user that owns the repo."
  type        = string
}

variable "github_repo" {
  description = "GitHub repo name (without org prefix)."
  type        = string
}

variable "roles" {
  description = <<-EOT
    List of IAM roles to create for GitHub Actions to assume via OIDC.

    Each role's `claim` is matched against the `sub` field of the GitHub OIDC
    token. Common values:
      - "ref:refs/heads/main"   — push to main
      - "pull_request"          — any PR event
      - "environment:<name>"    — deployment to a GitHub environment
  EOT
  type = list(object({
    name        = string
    claim       = string
    policy_arns = list(string)
  }))
}
