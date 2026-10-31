# What `terraform apply` prints at the end (and `terraform output` any time).

output "public_ip" {
  description = "The fixed IP. Type it into duckdns.org once."
  value       = aws_eip.server.public_ip
}

output "instance_id" {
  description = "The server's id, for Session Manager."
  value       = aws_instance.server.id
}

output "connect" {
  description = "Paste this to get a shell on the server (no SSH)."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.server.id}"
}
