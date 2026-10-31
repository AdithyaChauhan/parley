# Two private image stores (ECR), one per image (D31). GitHub pushes to them,
# the server pulls from them.

resource "aws_ecr_repository" "parley" {
  for_each = toset(["parley-backend", "parley-web"])
  name     = each.key

  # A version tag, once pushed, can never point at a different image. So
  # "a410b04" always means exactly the image built from commit a410b04.
  image_tag_mutability = "IMMUTABLE"

  # A free check of each new image for known security holes (basic scan).
  image_scanning_configuration {
    scan_on_push = true
  }

  # `terraform destroy` removes the stores even with images inside. Nothing is
  # lost: every image can be built again from Git (D29).
  force_delete = true
}

# Keep only the newest 10 images in each store, so storage stays at cents.
# The rollback can go back up to 10 versions.
resource "aws_ecr_lifecycle_policy" "keep_last_10" {
  for_each   = aws_ecr_repository.parley
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
