locals {
  PROD_STATE_BUCKET_ARN = "arn:aws:s3:::${var.state_bucket_prod}"
  PROD_FUNCTION_ARN     = "arn:aws:lambda:${var.region}:${data.aws_caller_identity.current.account_id}:function:gcorg-resolver-prod"
  PROD_LOG_GROUP_ARN    = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/gcorg-resolver-prod"
}

# --- Prod plan role ---------------------------------------------------------

data "aws_iam_policy_document" "plan_state_prod" {
  statement {
    sid       = "ListStateBucket"
    actions   = ["s3:ListBucket"]
    resources = [local.PROD_STATE_BUCKET_ARN]
  }

  statement {
    sid = "ReadWriteProdStateObjects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    # prod state lives at prod/lambda-api/*
    resources = ["${local.PROD_STATE_BUCKET_ARN}/prod/lambda-api*"]
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
      local.PROD_STATE_BUCKET_ARN,
      "${local.PROD_STATE_BUCKET_ARN}/prod/lambda-api*",
    ]
  }

  statement {
    sid     = "LambdaProd"
    actions = ["lambda:*"]
    resources = [
      local.PROD_FUNCTION_ARN,
      "${local.PROD_FUNCTION_ARN}:*",
    ]
  }

  # HTTP API ids aren't known until creation; tags are managed under /tags
  statement {
    sid     = "ApiGatewayHttpApis"
    actions = ["apigateway:*"]
    resources = [
      "arn:aws:apigateway:${var.region}::/apis",
      "arn:aws:apigateway:${var.region}::/apis/*",
      "arn:aws:apigateway:${var.region}::/tags/*",
    ]
  }

  statement {
    sid     = "LogsProd"
    actions = ["logs:*"]
    resources = [
      local.PROD_LOG_GROUP_ARN,
      "${local.PROD_LOG_GROUP_ARN}:*",
    ]
  }

  # DescribeLogGroups has no resource-level permissions
  statement {
    sid       = "LogsDescribe"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }

  statement {
    sid     = "IamProdRoles"
    actions = ["iam:*"]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/gcorg-resolver-prod*",
    ]
  }

  statement {
    sid       = "IamPassProdRoles"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/gcorg-resolver-prod*"]
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

# --- Weekly cost report role -----------------------------------------------

data "aws_iam_policy_document" "cost_report_read" {
  statement {
    sid = "CostExplorerRead"
    actions = [
      "ce:GetCostAndUsage",
      "ce:GetDimensionValues",
      "ce:GetTags",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "cost_report_read" {
  name        = "gcorg-resolver-cost-report-read"
  description = "Read-only Cost Explorer permissions for weekly account cost reports."
  policy      = data.aws_iam_policy_document.cost_report_read.json
}

# --- OIDC provider + roles --------------------------------------------------

module "github_oidc" {
  source = "github.com/cds-snc/terraform-modules//gh_oidc_role?ref=v13.2.0"

  billing_tag_value = var.billing_tag_value
  org_name          = var.github_org
  oidc_exists       = false

  roles = [
    {
      name      = "gcorg-resolver-plan-prod"
      repo_name = var.github_repo
      claim     = "pull_request"
    },
    {
      name      = "gcorg-resolver-apply-prod"
      repo_name = var.github_repo
      claim     = "ref:refs/heads/main"
    },
    {
      name      = "Billing-ReadOnly"
      repo_name = var.github_repo
      claim     = "ref:refs/heads/main"
    },
  ]
}

# The upstream module creates roles without policies, so attachments live here.
# Keys are static so the instances are known at plan time.
locals {
  ROLE_POLICIES = {
    "gcorg-resolver-plan-prod::readonly" = { role = "gcorg-resolver-plan-prod", policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess" }
    "gcorg-resolver-plan-prod::state"    = { role = "gcorg-resolver-plan-prod", policy_arn = aws_iam_policy.plan_state_prod.arn }
    "gcorg-resolver-apply-prod::apply"   = { role = "gcorg-resolver-apply-prod", policy_arn = aws_iam_policy.apply_prod.arn }
    "Billing-ReadOnly::cost-report"      = { role = "Billing-ReadOnly", policy_arn = aws_iam_policy.cost_report_read.arn }
  }
}

resource "aws_iam_role_policy_attachment" "role_policies" {
  for_each = local.ROLE_POLICIES

  role       = module.github_oidc.roles[each.value.role].name
  policy_arn = each.value.policy_arn
}

# --- State moves from the in-repo github-oidc module -------------------------

moved {
  from = module.github_oidc.aws_iam_openid_connect_provider.github
  to   = module.github_oidc.aws_iam_openid_connect_provider.github[0]
}

moved {
  from = module.github_oidc.aws_iam_role_policy_attachment.this["gcorg-resolver-plan-prod::0"]
  to   = aws_iam_role_policy_attachment.role_policies["gcorg-resolver-plan-prod::readonly"]
}

moved {
  from = module.github_oidc.aws_iam_role_policy_attachment.this["gcorg-resolver-plan-prod::1"]
  to   = aws_iam_role_policy_attachment.role_policies["gcorg-resolver-plan-prod::state"]
}

moved {
  from = module.github_oidc.aws_iam_role_policy_attachment.this["gcorg-resolver-apply-prod::0"]
  to   = aws_iam_role_policy_attachment.role_policies["gcorg-resolver-apply-prod::apply"]
}

moved {
  from = module.github_oidc.aws_iam_role_policy_attachment.this["Billing-ReadOnly::0"]
  to   = aws_iam_role_policy_attachment.role_policies["Billing-ReadOnly::cost-report"]
}
