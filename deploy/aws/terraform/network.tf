# Parley's own small network (D30): Mumbai has no default VPC, so we build
# one. All four pieces are free, and `terraform destroy` removes them.

# The zones (separate data centres) in the region that are up right now.
data "aws_availability_zones" "available" {
  state = "available"
}

# The VPC: a private network only Parley's resources live in.
# 10.0.0.0/16 = room for 65,536 private addresses, far more than we need.
resource "aws_vpc" "parley" {
  cidr_block = "10.0.0.0/16"
  # Let the server look up names (like download.docker.com) and get one itself.
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "parley" }
}

# The internet gateway: the network's door to the internet, both ways.
resource "aws_internet_gateway" "parley" {
  vpc_id = aws_vpc.parley.id

  tags = { Name = "parley" }
}

# One "public" subnet (a slice of the VPC) in one zone. It's public because its
# route table (below) sends internet traffic through the gateway.
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.parley.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  # A temporary public IP at boot, so user_data can download Docker before the
  # Elastic IP is attached. AWS drops it once the Elastic IP takes over.
  map_public_ip_on_launch = true

  tags = { Name = "parley-public" }
}

# The route table: "anything not inside the VPC goes out through the gateway".
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.parley.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.parley.id
  }

  tags = { Name = "parley-public" }
}

# Links the subnet to that route table (a link only, so it has no tags).
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
