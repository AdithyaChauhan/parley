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
