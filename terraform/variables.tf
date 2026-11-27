variable "project_name" {
  description = "Prefijo para nombrar los recursos"
  type        = string
  default     = "notas-universidad"
}

variable "aws_region" {
  description = "Región de AWS"
  type        = string
  default     = "us-east-2"
}

# ---------- Red ----------
variable "vpc_cidr" {
  description = "Rango de la VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Subredes públicas (ALB y EC2), una por AZ"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "Subredes privadas (RDS), una por AZ"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24"]
}

variable "admin_cidr" {
  description = "IP autorizada para SSH, en formato x.x.x.x/32 (tu IP pública)"
  type        = string

  validation {
    condition     = var.admin_cidr != "0.0.0.0/0" && can(cidrhost(var.admin_cidr, 0))
    error_message = "admin_cidr debe ser un CIDR válido y NO puede ser 0.0.0.0/0."
  }
}

# ---------- Cómputo ----------
variable "instance_type" {
  description = "Tipo de instancia EC2"
  type        = string
  default     = "t3.micro"
}

variable "public_key" {
  description = "Contenido de tu llave pública SSH (archivo .pub)"
  type        = string
}

variable "app_port" {
  description = "Puerto donde escucha el contenedor en cada EC2"
  type        = number
  default     = 8000
}

# ---------- Base de datos ----------
variable "db_name" {
  type    = string
  default = "notas"
}

variable "db_username" {
  type    = string
  default = "notas_app"
}

variable "db_password" {
  description = "Contraseña de RDS (mín. 8 caracteres, sin / @ \" ni espacios)"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 8 && !can(regex("[/@\" ]", var.db_password))
    error_message = "La contraseña debe tener mínimo 8 caracteres y no incluir / @ \" ni espacios."
  }
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "db_multi_az" {
  description = "RDS Multi-AZ (reto opcional; duplica el costo de la BD)"
  type        = bool
  default     = false
}

# ---------- Ansible ----------
variable "ssh_user" {
  description = "Usuario SSH de la AMI (Ubuntu = ubuntu)"
  type        = string
  default     = "ubuntu"
}

variable "ssh_private_key_path" {
  description = "Ruta de la llave privada DESDE WSL, usada en el inventario de Ansible"
  type        = string
  default     = "~/.ssh/notas-aws"
}
