locals {
  state_bucket_arn = "arn:aws:s3:::${var.state_bucket}"
}

# --- Dev plan role ----------------------------------------------------------

data "aws_iam_policy_document" "plan_state_dev" {
  statement {
    sid       = "ListStateBucket"
    actions   = ["s3:ListBucket"]
    resources = [local.state_bucket_arn]
  }

  statement {
    sid = "ReadWriteDevStateObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    # dev state lives at lambda-api/* (no env prefix — existing key)
    resources = ["${local.state_bucket_arn}/lambda-api*"]
  }
}

resource "aws_iam_policy" "plan_state_dev" {
  name        = "gcorg-resolver-plan-state-dev"
  description = "State bucket access for the dev plan role."
  policy      = data.aws_iam_policy_document.plan_state_dev.json
}

# --- Dev apply role ---------------------------------------------------------

data "aws_iam_policy_document" "apply_dev" {
  statement {
    sid     = "StateBucketDev"
    actions = ["s3:*"]
    resources = [
      local.state_bucket_arn,
      "${local.state_bucket_arn}/lambda-api*",
    ]
  }

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

  statement {
    sid     = "IamDevRoles"
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::${var.account_id}:role/gcorg-resolver-dev*",
    ]
  }

  statement {
    sid       = "IamPassDevRoles"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/gcorg-resolver-dev*"]
  }

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

resource "aws_iam_policy" "apply_dev" {
  name        = "gcorg-resolver-apply-dev"
  description = "Scoped permissions for the CI dev apply role."
  policy      = data.aws_iam_policy_document.apply_dev.json
}

# --- Prod plan role ---------------------------------------------------------

data "aws_iam_policy_document" "plan_state_prod" {
  statement {
    sid       = "ListStateBucket"
    actions   = ["s3:ListBucket"]
    resources = [local.state_bucket_arn]
  }

  statement {
    sid = "ReadWriteProdStateObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    # prod state lives at prod/*
    resources = ["${local.state_bucket_arn}/prod*"]
  }
}

resource "aws_iam_policy" "plan_state_prod" {
  name        = "gcorg-resolver-plan-state-prod"
  description = "State bucket access for the prod plan role."
  policy      = data.aws_iam_policy_document.plan_state_prod.json
}

# --- Prod apply role --------------------------------------------------------

data "aws_iam_policy_document" "apply_prod" {
  statement {
    sid     = "StateBucketProd"
    actions = ["s3:*"]
    resources = [
      local.state_bucket_arn,
      "${local.state_bucket_arn}/prod*",
    ]
  }

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

  statement {
    sid     = "IamProdRoles"
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::${var.account_id}:role/gcorg-resolver-prod*",
    ]
  }

  statement {
    sid       = "IamPassProdRoles"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${var.account_id}:role/gcorg-resolver-prod*"]
  }

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

resource "aws_iam_policy" "apply_prod" {
  name        = "gcorg-resolver-apply-prod"
  description = "Scoped permissions for the CI prod apply role."
  policy      = data.aws_iam_policy_document.apply_prod.json
}

# --- OIDC provider + roles --------------------------------------------------

module "github_oidc" {
  source = "../../../aws/github-oidc"

  github_org  = var.github_org
  github_repo = var.github_repo

  roles = [
    {
      name  = "gcorg-resolver-plan-dev"
      claim = "pull_request"
      policy_arns = [
        "arn:aws:iam::aws:policy/ReadOnlyAccess",
        aws_iam_policy.plan_state_dev.arn,
      ]
    },
    {
      name  = "gcorg-resolver-apply-dev"
      claim = "ref:refs/heads/dev"
      policy_arns = [
        aws_iam_policy.apply_dev.arn,
      ]
    },
    {
      name  = "gcorg-resolver-plan-prod"
      claim = "pull_request"
      policy_arns = [
        "arn:aws:iam::aws:policy/ReadOnlyAccess",
        aws_iam_policy.plan_state_prod.arn,
      ]
    },
    {
      name  = "gcorg-resolver-apply-prod"
      claim = "ref:refs/heads/main"
      policy_arns = [
        aws_iam_policy.apply_prod.arn,
      ]
    },
  ]
}
