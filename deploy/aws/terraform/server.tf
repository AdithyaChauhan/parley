# The server itself: firewall, a role for Session Manager, the EC2 machine and
# its fixed IP (D30).

# The firewall (security group). Only web traffic comes in: no 22 (SSH), and
# no database, Redis or RabbitMQ ports.
resource "aws_security_group" "web" {
  name        = "parley-web"
  description = "Parley: only HTTP and HTTPS in"
  vpc_id      = aws_vpc.parley.id

  ingress {
    description = "HTTP: the Lets Encrypt check, and a redirect to https"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS: Parley itself"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Going out is open: apt, Docker images, git clone, Let's Encrypt, the push
  # services, and Session Manager (the server calls AWS, AWS never calls in).
  egress {
    description = "Everything out"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "parley-web" }
}

# A role the server wears. It says "EC2 machines may use this role"...
resource "aws_iam_role" "server" {
  name = "parley-server"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# ...and allows only one thing: talking to Session Manager, so we get a shell
# with no SSH port and no key file (D30).
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.server.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Our account's id, for the Parameter Store addresses below.
data "aws_caller_identity" "me" {}

# What else the server may do in AWS (D31): pull Parley's images, read its
# secrets under /parley/prod, and send container logs to CloudWatch. All of it
# runs on the server itself, never inside a container (hop limit 1, above).
resource "aws_iam_role_policy" "server_deploy" {
  name = "pull-images-read-secrets-write-logs"
  role = aws_iam_role.server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        # Pull only, from Parley's two stores. The server can't push.
        Sid      = "PullParleyImages"
        Effect   = "Allow"
        Action   = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
        Resource = [for repo in aws_ecr_repository.parley : repo.arn]
      },
      {
        # Read the secrets (the folder itself, and everything in it).
        Sid    = "ReadParleySecrets"
        Effect = "Allow"
        Action = ["ssm:GetParametersByPath", "ssm:GetParameters", "ssm:GetParameter"]
        Resource = [
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/parley/prod",
          "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/parley/prod/*",
        ]
      },
      {
        # Docker's CloudWatch log driver: one stream per container, in our group.
        Sid      = "WriteContainerLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.containers.arn}:*"
      },
    ]
  })
}

# Write access to the secrets, only while store-secrets.sh runs once (D31).
# count = 0 means "this doesn't exist": the second apply, with
# allow_secret_upload = false, removes it again.
resource "aws_iam_role_policy" "server_secret_upload" {
  count = var.allow_secret_upload ? 1 : 0
  name  = "store-secrets-once"
  role  = aws_iam_role.server.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "StoreParleySecrets"
      Effect   = "Allow"
      Action   = "ssm:PutParameter"
      Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.me.account_id}:parameter/parley/prod/*"
    }]
  })
}

# The holder that attaches the role to the machine.
resource "aws_iam_instance_profile" "server" {
  name = "parley-server"
  role = aws_iam_role.server.name
}

# Canonical's own pointer to today's Ubuntu 24.04 LTS image for x86.
# insecure_value: the plain value (an image id is no secret), so the plan shows it.
data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

resource "aws_instance" "server" {
  ami                    = data.aws_ssm_parameter.ubuntu.insecure_value
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.server.name

  # Runs once, on the first boot: installs Docker and the Compose plugin.
  # replace() drops Windows line endings (Git's autocrlf on the laptop), which
  # would break bash on the server.
  user_data = replace(file("${path.module}/user_data.sh"), "\r", "")

  # When the CPU budget runs out, slow down instead of billing extra (D30).
  credit_specification {
    cpu_credits = "standard"
  }

  # The metadata service (where a server asks AWS about itself, and gets its
  # role's keys): IMDSv2 only, which needs a token first. Hop limit 1: the token
  # can't reach inside a Docker container, so a hacked container can't borrow
  # the server's role. The app never needs AWS (D29).
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size = var.disk_gb
    volume_type = "gp3"
    encrypted   = true
    tags        = { Name = "parley" }
  }

  tags = { Name = "parley" }

  lifecycle {
    # The pointer above moves to a new image every week or so. Without this,
    # every plan would want to replace the server (and its data) (D30).
    ignore_changes = [ami]
  }
}

# The fixed public IP (Elastic IP). It stays the same through stops and starts,
# so DuckDNS is set once.
resource "aws_eip" "server" {
  domain   = "vpc"
  instance = aws_instance.server.id

  tags = { Name = "parley" }

  # The IP only works once the network has its internet door.
  depends_on = [aws_internet_gateway.parley]
}
