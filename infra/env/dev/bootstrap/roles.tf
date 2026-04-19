locals {
  state_bucket_arn = "arn:aws:s3:::${var.state_bucket}"
  app_name_glob    = "gcorg-resolver-${var.env}*"
}

# --- Plan role: read-only AWS + full state bucket access --------------------

# Terraform plan refreshes state, which can write the state object and the
# native S3 lockfile. Scope is the app's state bucket only.
data "aws_iam_policy_document" "plan_state" {
  statement {
    sid       = "ListStateBucket"
    actions   = ["s3:ListBucket"]
    resources = [local.state_bucket_arn]
  }

  statement {
    sid = "ReadWriteStateObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${local.state_bucket_arn}/*"]
  }
}

resource "aws_iam_policy" "plan_state" {
  name        = "gcorg-resolver-plan-state"
  description = "Access to the Terraform state bucket for the plan role."
  policy      = data.aws_iam_policy_document.plan_state.json
}

# --- Apply role: scoped write access to the services this stack uses --------

data "aws_iam_policy_document" "apply" {
  statement {
    sid     = "StateBucket"
    actions = ["s3:*"]
    resources = [
      local.state_bucket_arn,
      "${local.state_bucket_arn}/*",
    ]
  }

  # Lambda and API Gateway don't support meaningful ARN-level IAM for most of
  # the actions Terraform calls (CreateFunction, CreateApi, etc. require
  # resource "*"). Scoping by service is the practical limit.
  statement {
    sid       = "LambdaAll"
    actions   = ["lambda:*"]
    resources = ["*"]
  }

  statement {
    sid       = "ApiGatewayAll"
    actions   = ["apigateway:*"]
    resources = ["*"]
  }

  statement {
    sid       = "LogsAll"
    actions   = ["logs:*"]
    resources = ["*"]
  }

  statement {
    sid       = "AcmAll"
    actions   = ["acm:*"]
    resources = ["*"]
  }

  # IAM is scoped to the app's role name prefix so the apply role cannot
  # modify the OIDC provider, the bootstrap roles, or unrelated account IAM.
  statement {
    sid     = "IamAppRoles"
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::${var.account_id}:role/${local.app_name_glob}",
    ]
  }

  statement {
    sid       = "IamPassAppRoles"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/${local.app_name_glob}"]
  }

  # Read-only IAM calls Terraform makes during planning that have no
  # resource-level scoping.
  statement {
    sid = "IamRead"
    actions = [
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicies",
      "iam:ListPolicyVersions",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "apply" {
  name        = "gcorg-resolver-apply"
  description = "Scoped permissions for the CI apply role."
  policy      = data.aws_iam_policy_document.apply.json
}

# --- OIDC provider + roles --------------------------------------------------

module "github_oidc" {
  source = "../../../aws/github-oidc"

  github_org  = var.github_org
  github_repo = var.github_repo

  roles = [
    {
      name  = "gcorg-resolver-plan"
      claim = "pull_request"
      policy_arns = [
        "arn:aws:iam::aws:policy/ReadOnlyAccess",
        aws_iam_policy.plan_state.arn,
      ]
    },
    {
      name  = "gcorg-resolver-apply"
      claim = "ref:refs/heads/main"
      policy_arns = [
        aws_iam_policy.apply.arn,
      ]
    },
  ]
}
