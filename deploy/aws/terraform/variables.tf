# The few settings worth changing without touching the other files.

variable "region" {
  description = "AWS region. Mumbai is the closest to India (D30)."
  type        = string
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "Server size. t3.small: x86, 2 vCPUs, 2 GB (sized from docker stats, D30)."
  type        = string
  default     = "t3.small"
}

variable "disk_gb" {
  description = "Disk size in GB: Ubuntu, Docker images and build cache, and the data."
  type        = number
  default     = 20
}

variable "github_repo" {
  description = "The only GitHub repo allowed to deploy, and only from main (D31), as GitHub's ID card names it: owner@owner-id/repo@repo-id. The ids never change, so a new repo with the same name can't get in (GitHub's immutable subject format, found in T29)."
  type        = string
  default     = "AdithyaChauhan@91404342/parley@1423740237"
}

variable "alert_email" {
  description = "Where alarm emails go. No default: set it in terraform.tfvars, which is gitignored (D31)."
  type        = string
}

variable "allow_secret_upload" {
  description = "true only while store-secrets.sh runs on the server: lets it write /parley/prod/* once, then apply again with false (D31)."
  type        = bool
  default     = false
}
