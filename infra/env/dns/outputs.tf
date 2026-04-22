output "nameservers" {
  description = "AWS nameservers for gcorgs.cdssandbox.xyz."
  value       = aws_route53_zone.gcorgs.name_servers
}

output "zone_id" {
  description = "Route 53 hosted zone ID for gcorgs.cdssandbox.xyz."
  value       = aws_route53_zone.gcorgs.zone_id
}