# Public hosted zone for gcorgs.cdssandbox.xyz

# The parent zone (cdssandbox.xyz) is managed by CDS SRE. The subdomain
# is delegated via NS records.

resource "aws_route53_zone" "gcorgs" {
  name = "gcorgs.cdssandbox.cyz"
}