variable "region" {
  type = string
}

variable "pathprefix" {
  type = string
}

variable "pathsuffix" {
  type = string
}

variable "bastioninstancetype" {
  type    = string
  default = "t2.micro"
}

variable "ingress_list" {
  type        = list(number)
  description = "list of ingress port"
}

variable "key_name" {
  type = string
}

variable "ami_name" {
  type = string
}

variable "aws_profile" {
  type = string
}