provider "aws" {
  region                  = var.region
  shared_credentials_files = [ "${var.pathprefix}/${var.pathsuffix}" ]
  profile                 = var.aws_profile
}