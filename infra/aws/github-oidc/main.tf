data "aws_caller_identity" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  roles_by_name = { for r in var.roles : r.name => r }
}

data "aws_iam_policy_document" "assume" {
  for_each = local.roles_by_name

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}/${var.github_repo}:${each.value.claim}"]
    }
  }
}

resource "aws_iam_role" "this" {
  for_each = local.roles_by_name

  name               = each.value.name
  assume_role_policy = data.aws_iam_policy_document.assume[each.key].json
}

resource "aws_iam_role_policy_attachment" "this" {
  # Key on role name + policy index (both static) so Terraform can determine
  # the full set of instances at plan time, even when policy ARNs are computed.
  for_each = {
    for pair in flatten([
      for role_name, role in local.roles_by_name : [
        for idx, policy_arn in role.policy_arns : {
          key        = "${role_name}::${idx}"
          role_name  = role_name
          policy_arn = policy_arn
        }
      ]
    ]) : pair.key => pair
  }

  role       = aws_iam_role.this[each.value.role_name].name
  policy_arn = each.value.policy_arn
}
