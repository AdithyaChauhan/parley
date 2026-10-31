# Running Parley on a server

Parley runs the same way everywhere: Docker Compose starts all of it. On a
laptop that's `docker compose --profile app up --build` (http://localhost:8080).
On a server, `docker-compose.prod.yml` adds what a public site needs: HTTPS,
no open database ports, restarts and log limits. AWS is optional (D29).

```
deploy/
  server/          works on any Linux server
    setup.sh           Docker, 2 GB swap, git clone (run once)
    .env.prod.example  every setting the server needs
    first-cert.sh      first HTTPS certificate, then starts Parley (run once)
    deploy.sh          puts new code live
    nginx.prod.conf    Nginx with HTTPS (port 80 only redirects)
  aws/             only for AWS
    terraform/              the server, image stores, deploy role, alarms
    store-secrets.sh        copies .env into Parameter Store (run once)
    deploy-from-ecr.sh      puts one version live from ECR (GitHub runs it)
    docker-compose.ecr.yml  images from ECR, logs to CloudWatch
```

## 1. Any Linux server

You need: Ubuntu or Debian, at least 2 GB of memory, a domain name pointing at
the server's IP, and ports 80 and 443 open to the internet. Nothing else needs
to be open.

**Set up (once).** As a user that can sudo:

```bash
curl -fsSL https://raw.githubusercontent.com/AdithyaChauhan/parley/main/deploy/server/setup.sh | bash
```

Then log out and back in (so the `docker` group applies), and make the
settings. Each secret is made on the server and goes straight into `.env`, so it
never shows on screen or leaves the server:

```bash
cd /opt/parley
cp deploy/server/.env.prod.example .env && chmod 600 .env
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" .env
sed -i "s/^RABBITMQ_PASSWORD=.*/RABBITMQ_PASSWORD=$(openssl rand -hex 24)/" .env
sed -i "s/^JWT_SECRET=.*/JWT_SECRET=$(openssl rand -hex 48)/" .env
sed -i "s/^VAPID_SUBJECT=.*/VAPID_SUBJECT=mailto:you@example.com/" .env   # your address
```

Build the images, then make the server's own push keys (the command is in
`.env.prod.example`; delete the two `change-me` VAPID lines first, then append
its output with `>> .env`):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app build
grep -c change-me .env    # 0 when every setting is filled in
```

**Go live (once).** Gets the first certificate from Let's Encrypt, starts
Parley, and proves that renewals work:

```bash
bash deploy/server/first-cert.sh your.domain.example you@example.com
```

The `certbot` service renews the certificate by itself (it checks twice a day
and renews 30 days before the 90 days run out), and Nginx reloads every 6 hours
to pick it up.

**Put new code live.**

```bash
bash deploy/server/deploy.sh        # anything changed
bash deploy/server/deploy.sh web    # only the frontend or Nginx: backend copies keep running
```

**Useful commands** (in `/opt/parley`; `c` is just a shortcut):

```bash
c() { docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app "$@"; }
c ps                      # what's running
c logs -f --tail 50 web   # follow one service's log
c stop backend_a          # failover demo: the apps move to backend_b
c start backend_a
```

**Known gaps:** no backups yet (the database lives in the `db_data` volume on
this one disk), and images are built on the server itself (on AWS, GitHub
builds them instead: part 3).

## 2. On AWS, with Terraform

`deploy/aws/terraform/` builds everything the server needs in Mumbai
(`ap-south-1`): a small network, a firewall that lets in only 80 and 443 (no
SSH), a t3.small Ubuntu 24.04 server with an encrypted 20 GB disk and Docker
already installed, and a fixed IP (Elastic IP). Every resource is tagged
`project=parley`. Cost: about $22 a month (D30).

You need: the AWS CLI (logged in with `aws configure`), the Session Manager
plugin, and Terraform 1.16.

```bash
cd deploy/aws/terraform
terraform init
terraform plan -out=parley.tfplan    # shows what would be built; changes nothing
terraform apply parley.tfplan        # builds exactly that plan
```

At the end it prints `public_ip` (point your domain at it) and `connect`, the
command for a shell on the server:

```bash
aws ssm start-session --region ap-south-1 --target <instance_id>
```

There's no SSH and no key file: Session Manager connects through AWS, using
the server's role. Then follow part 1 from "Set up" (Docker is already there,
so `setup.sh` skips it).

`terraform.tfstate` (Terraform's record of what it built) stays only on the
laptop and is never committed. Keep a private backup copy: without it,
Terraform can't remove the server for you.

## 3. On AWS: deploys from GitHub

Merging into `main` puts it live by itself (`.github/workflows/deploy.yml`):

```
CI green on main → build parley-backend + parley-web, tagged with the commit
  → log in to AWS with OIDC (no AWS keys stored in GitHub)
  → push both images to ECR → run the parley-deploy SSM document on the server
server: .env from Parameter Store → pull → migrate → backend_a → 15 s →
  backend_b → worker → web (only if it changed) → /api/health shows the commit
```

The backend copies restart one at a time, so chats keep working. Table
changes must work for the old copy too, which runs on the new tables for a
moment: add in one deploy, remove in a later one.

**Set up (once).** Terraform needs your alarm email in
`deploy/aws/terraform/terraform.tfvars` (gitignored):

```
alert_email = "you@example.com"
```

1. `terraform plan -var allow_secret_upload=true -out=parley.tfplan`, then
   `terraform apply parley.tfplan`. Click "Confirm subscription" in the email AWS
   sends.
2. On the server: `sudo snap install aws-cli --classic`, then
   `bash deploy/aws/store-secrets.sh`. It copies `.env` into Parameter Store
   (`/parley/prod/*`, encrypted) without showing any value.
3. `terraform plan -out=parley.tfplan` and apply again: this removes the
   server's write access to the secrets. From now on it can only read them.
4. On GitHub, Settings > Secrets and variables > Actions > **Variables** (not
   secrets): `AWS_ROLE_ARN` (`terraform output github_role_arn`), `AWS_REGION`
   (`ap-south-1`), `INSTANCE_ID` (`terraform output instance_id`) and
   `SITE_URL` (`https://your.domain.example`).

**Roll back.** Actions > Deploy > Run workflow, from `main`, with an older
version (one of the last 10 commits in ECR, from this setup on).

**Who can do what.** GitHub's role only works for this repo's `main`, may
only push to the two image stores, and may only run `parley-deploy` (which
takes nothing but a commit id) on this one server. It can't read the secrets.
The server can pull images, read `/parley/prod/*` and write its logs.

**Change a secret.** In the AWS console: Systems Manager > Parameter Store,
edit the value, then run the Deploy workflow again (the server rewrites `.env`
from it on every deploy).

**Logs and alarms.** Parley's containers log to CloudWatch
(`/parley/containers`, kept 7 days); `docker compose logs` on the server still
works. An email goes out when the server fails its status checks or stops
reporting, or its CPU stays above 80% for 15 minutes.

The server now sits on an exact commit, not a branch, so
`deploy/server/deploy.sh` stops there with "This server is deployed by
GitHub Actions".

## 4. Turning it all off

```bash
cd deploy/aws/terraform
terraform plan -destroy    # shows everything that would be removed; changes nothing
terraform destroy          # asks "yes", then removes the server, disk, IP and network
```

This deletes the server's disk, so the live database and chats are gone for
good, and also the image stores, the deploy role and the alarms. The billing
stops when it finishes. The secrets in Parameter Store aren't Terraform's
(store-secrets.sh made them) and cost nothing, but delete them too:

```bash
aws ssm get-parameters-by-path --path /parley/prod --query 'Parameters[].Name' --output text \
  | xargs aws ssm delete-parameters --names
``` Only stopping the server isn't
enough: the disk and the Elastic IP still cost about $5.50 a month.

Nothing else depends on AWS: deleting `deploy/aws/` or running `terraform
destroy` never breaks the project, and it still runs on a laptop with one
command (D29).
