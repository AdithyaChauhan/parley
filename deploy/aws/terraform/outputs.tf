# What `terraform apply` prints at the end (and `terraform output` any time).

output "public_ip" {
  description = "The fixed IP. Type it into duckdns.org once."
  value       = aws_eip.server.public_ip
}

output "instance_id" {
  description = "The server's id, for Session Manager."
  value       = aws_instance.server.id
}

output "github_role_arn" {
  description = "For GitHub's AWS_ROLE_ARN variable (D31). Not a secret: only this repo on main can use it."
  value       = aws_iam_role.github_deploy.arn
}

output "ecr_registry" {
  description = "The address of Parley's image stores (ECR)."
  value       = split("/", aws_ecr_repository.parley["parley-backend"].repository_url)[0]
}

output "connect" {
  description = "Paste this to get a shell on the server (no SSH)."
  value       = "aws ssm start-session --region ${var.region} --target ${aws_instance.server.id}"
}
