variable "aws_region" {
  default = "ap-south-1"
}

variable "project" {
  default = "uksf-qr"
}

variable "environment" {
  default = "dev"
}

variable "admin_cidr" {
  type = string
}

variable "ssh_public_key_path" {
  default = "~/.ssh/qr-dev.pub"
}

variable "db_name" {
  default = "uksf_dev"
}

variable "db_username" {
  default = "qradmin"
}

variable "db_password" {
  type      = string
  sensitive = true
}
