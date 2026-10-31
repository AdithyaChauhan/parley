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
  aws/terraform/   only for AWS: builds the server itself
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
this one disk), and images are built on the server itself.

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

## 3. Turning it all off

```bash
cd deploy/aws/terraform
terraform plan -destroy    # shows everything that would be removed; changes nothing
terraform destroy          # asks "yes", then removes the server, disk, IP and network
```

This deletes the server's disk, so the live database and chats are gone for
good. The billing stops when it finishes. Only stopping the server isn't
enough: the disk and the Elastic IP still cost about $5.50 a month.

Nothing else depends on AWS: deleting `deploy/aws/` or running `terraform
destroy` never breaks the project, and it still runs on a laptop with one
command (D29).
