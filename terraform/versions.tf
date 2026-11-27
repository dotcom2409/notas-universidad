terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }

  # State LOCAL (terraform.tfstate en esta carpeta, excluido de Git por .gitignore).
  # Contiene datos sensibles (p. ej. la contraseña de RDS), por eso NUNCA se publica.
  # Mejora para producción: backend "s3" cifrado + bloqueo de estado.
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "Terraform"
    }
  }
}
