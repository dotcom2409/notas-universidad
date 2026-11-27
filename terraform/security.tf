# ---------------- ALB: único punto público ----------------
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-sg-alb"
  description = "HTTP publico hacia el ALB"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project_name}-sg-alb" }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "HTTP desde Internet"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_a_app" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Solo hacia las EC2 en el puerto de la app"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

# ---------------- EC2: app solo desde el ALB ----------------
resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg-app"
  description = "App solo desde el ALB; SSH solo desde IP admin"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project_name}-sg-app" }
}

resource "aws_vpc_security_group_ingress_rule" "app_desde_alb" {
  security_group_id            = aws_security_group.app.id
  description                  = "Trafico de la app solo desde el SG del ALB"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

resource "aws_vpc_security_group_ingress_rule" "app_ssh_admin" {
  security_group_id = aws_security_group.app.id
  description       = "SSH solo desde la IP del administrador"
  cidr_ipv4         = var.admin_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

resource "aws_vpc_security_group_egress_rule" "app_salida" {
  security_group_id = aws_security_group.app.id
  description       = "Salida para paquetes, ECR y RDS"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ---------------- RDS: solo desde las EC2 ----------------
resource "aws_security_group" "db" {
  name        = "${var.project_name}-sg-db"
  description = "PostgreSQL solo desde el SG de la app"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.project_name}-sg-db" }
}

resource "aws_vpc_security_group_ingress_rule" "db_desde_app" {
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL desde las EC2"
  referenced_security_group_id = aws_security_group.app.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
