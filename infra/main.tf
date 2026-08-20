data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  name        = "${var.project}-${var.environment}"
  bucket_name = "${var.project}-${var.environment}-${data.aws_caller_identity.current.account_id}"
}


# =========================================================
# VPC
# =========================================================

resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${local.name}-vpc"
  }
}


# =========================================================
# INTERNET GATEWAY
# =========================================================

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${local.name}-igw"
  }
}


# =========================================================
# PUBLIC SUBNETS
# ALB + EC2
# =========================================================

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name}-public-a"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.20.2.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name = "${local.name}-public-b"
  }
}


# =========================================================
# PRIVATE DB SUBNETS
# =========================================================

resource "aws_subnet" "db_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.20.11.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${local.name}-db-a"
  }
}

resource "aws_subnet" "db_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.20.12.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${local.name}-db-b"
  }
}


# =========================================================
# PUBLIC ROUTING
# =========================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${local.name}-public-rt"
  }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}


# =========================================================
# ALB SECURITY GROUP
# =========================================================

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.20.0.0/16"]
  }

  tags = {
    Name = "${local.name}-alb-sg"
  }
}


# =========================================================
# APP SECURITY GROUP
# =========================================================

resource "aws_security_group" "app" {
  name   = "${local.name}-app-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-app-sg"
  }
}


# =========================================================
# DATABASE SECURITY GROUP
# =========================================================

resource "aws_security_group" "db" {
  name   = "${local.name}-db-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  tags = {
    Name = "${local.name}-db-sg"
  }
}


# =========================================================
# S3
# Photos + QR Codes
# =========================================================

resource "aws_s3_bucket" "assets" {
  bucket = local.bucket_name

  tags = {
    Name = "${local.name}-assets"
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# =========================================================
# ECR
# =========================================================

resource "aws_ecr_repository" "app" {
  name = "${var.project}-${var.environment}"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${local.name}-ecr"
  }
}


# =========================================================
# RDS POSTGRESQL
# =========================================================

resource "aws_db_subnet_group" "db" {
  name = "${local.name}-db-subnets"

  subnet_ids = [
    aws_subnet.db_a.id,
    aws_subnet.db_b.id
  ]
}

resource "aws_db_instance" "postgres" {
  identifier = "${local.name}-postgres"

  engine         = "postgres"
  engine_version = "16"

  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name = aws_db_subnet_group.db.name

  vpc_security_group_ids = [
    aws_security_group.db.id
  ]

  publicly_accessible = false
  multi_az            = false

  backup_retention_period = 1

  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name = "${local.name}-postgres"
  }
}


# =========================================================
# EC2 IAM ROLE
# =========================================================

resource "aws_iam_role" "ec2" {
  name = "${local.name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [{
      Effect = "Allow"

      Principal = {
        Service = "ec2.amazonaws.com"
      }

      Action = "sts:AssumeRole"
    }]
  })
}


# ECR Pull Permission

resource "aws_iam_role_policy_attachment" "ecr" {
  role = aws_iam_role.ec2.name

  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}


# S3 Permission

resource "aws_iam_role_policy" "s3" {
  name = "${local.name}-s3-policy"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]

        Resource = "${aws_s3_bucket.assets.arn}/*"
      },

      {
        Effect = "Allow"

        Action = [
          "s3:ListBucket"
        ]

        Resource = aws_s3_bucket.assets.arn
      }
    ]
  })
}


resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name}-profile"
  role = aws_iam_role.ec2.name
}


# =========================================================
# SSH KEY
# =========================================================

resource "aws_key_pair" "dev" {
  key_name = "${local.name}-key"

  public_key = file(
    pathexpand(var.ssh_public_key_path)
  )
}


# =========================================================
# EC2
# =========================================================

resource "aws_instance" "app" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.small"

  subnet_id = aws_subnet.public_a.id

  associate_public_ip_address = true

  vpc_security_group_ids = [
    aws_security_group.app.id
  ]

  key_name = aws_key_pair.dev.key_name

  iam_instance_profile = aws_iam_instance_profile.ec2.name

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  user_data = <<-EOF
    #!/bin/bash

    apt-get update -y
    apt-get install -y docker.io curl unzip

    systemctl enable --now docker
    usermod -aG docker ubuntu

    cd /tmp
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
    unzip -q awscliv2.zip
    ./aws/install
  EOF

  tags = {
    Name = "${local.name}-app"
  }
}


# =========================================================
# ALB
# =========================================================

resource "aws_lb" "app" {
  name = "${local.name}-alb"

  internal           = false
  load_balancer_type = "application"

  security_groups = [
    aws_security_group.alb.id
  ]

  subnets = [
    aws_subnet.public_a.id,
    aws_subnet.public_b.id
  ]
}


# =========================================================
# TARGET GROUP
# =========================================================

resource "aws_lb_target_group" "app" {
  name = "${local.name}-tg"

  port     = 8000
  protocol = "HTTP"

  vpc_id = aws_vpc.main.id

  health_check {
    path = "/health"

    matcher = "200"

    interval = 30
    timeout  = 5

    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}


resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn

  target_id = aws_instance.app.id

  port = 8000
}


# =========================================================
# ALB LISTENER
# =========================================================

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.app.arn

  port     = 80
  protocol = "HTTP"

  default_action {
    type = "forward"

    target_group_arn = aws_lb_target_group.app.arn
  }
}
