# How GitHub deploys Parley with no stored AWS keys (D31): it proves who it is
# with OIDC, gets a role that lasts an hour, pushes the images and runs one
# command on the server: the parley-deploy document below.

# GitHub's ID-card checker (the OIDC provider). It already exists in the account
# (made for the delivery-delay project), and AWS allows only one, so Parley only
# reads it. `terraform destroy` never deletes it (D31).
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

# The role GitHub wears. Only a run of this repo, on main, gets it.
resource "aws_iam_role" "github_deploy" {
  name = "parley-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        # Exact matches, no wildcards: another repo, another branch or a pull
        # request gets a different "sub" and is refused.
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

# What the role may do, and nothing more.
resource "aws_iam_role_policy" "github_deploy" {
  name = "push-images-and-deploy"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # The ECR log-in. AWS can't narrow this one to a repository; the push
        # rights below are what count.
        Sid      = "EcrLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # Push to Parley's two stores only, and list their tags (to skip a
        # version that's already there: tags can't be overwritten).
        # BatchGetImage: at the end of a push, Docker asks whether the image is
        # already there, and is refused without it (found in T29).
        Sid    = "PushParleyImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:DescribeImages",
        ]
        Resource = [for repo in aws_ecr_repository.parley : repo.arn]
      },
      {
        # Run the parley-deploy document on this one server. Both must match,
        # so no other document (like "run any shell command") and no other
        # server (D31).
        Sid      = "RunOnlyTheDeploy"
        Effect   = "Allow"
        Action   = "ssm:SendCommand"
        Resource = [aws_ssm_document.deploy.arn, aws_instance.server.arn]
      },
      {
        # Read how that command went (AWS can't narrow these reads).
        Sid      = "ReadDeployResult"
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"]
        Resource = "*"
      },
    ]
  })
}

# The only command GitHub may run on the server. It takes one thing, a version
# (a commit id, 7 to 40 hex characters), so nothing else can be slipped in.
# SSM runs it as root; the work itself runs as the repo's owner (ssm-user), so
# git never sees "dubious ownership" (T28).
resource "aws_ssm_document" "deploy" {
  name            = "parley-deploy"
  document_type   = "Command"
  document_format = "YAML"

  content = yamlencode({
    schemaVersion = "2.2"
    description   = "Put one Parley version (a commit) live on the server (D31)."
    parameters = {
      tag = {
        type           = "String"
        description    = "The commit to deploy, as tagged in ECR (for example a410b04)."
        allowedPattern = "^[0-9a-f]{7,40}$"
      }
    }
    mainSteps = [{
      action = "aws:runShellScript"
      name   = "deploy"
      inputs = {
        timeoutSeconds = "900"
        runCommand = [
          "set -eu",
          "cd /opt/parley",
          "OWNER=$(stat -c %U .)",
          # Check out exactly this commit, so a rollback also rolls back the
          # Compose files, nginx.prod.conf and the scripts (D31).
          "sudo -u \"$OWNER\" -H git fetch --quiet origin",
          "sudo -u \"$OWNER\" -H git checkout --quiet --detach {{ tag }}",
          "sudo -u \"$OWNER\" -H bash deploy/aws/deploy-from-ecr.sh {{ tag }}",
        ]
      }
    }]
  })
}
