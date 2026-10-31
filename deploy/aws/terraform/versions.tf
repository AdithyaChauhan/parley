# Which Terraform and which AWS plugin (a "provider") build Parley's server.
# Exact versions, like the Docker images (D27): an upgrade is a choice, never a surprise.

terraform {
  # Any 1.16 patch, never 1.17: a new minor version waits (D27, D30).
  required_version = "~> 1.16.0"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # The plugin that turns these files into AWS calls. It ships a new minor
      # every week, so we take one that's a few weeks old (D27).
      version = "= 6.67.0"
    }
  }

  # No "backend" block: the state (Terraform's receipt of what it built) stays
  # in a local file next to these, and is gitignored (D30).
}

provider "aws" {
  region = var.region

  # Put this tag on every resource that can carry one, so the console and the
  # bill can show "everything Parley" with one filter (D30).
  default_tags {
    tags = {
      project = "parley"
    }
  }
}
