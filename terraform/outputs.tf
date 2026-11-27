output "alb_url" {
  description = "URL pública de la aplicación (usar esta en la demo)"
  value       = "http://${aws_lb.app.dns_name}"
}

output "ec2_instancias" {
  description = "Instancias por AZ"
  value = {
    for i in aws_instance.app : i.tags.Name => {
      id         = i.id
      az         = i.availability_zone
      ip_publica = i.public_ip
      ip_privada = i.private_ip
    }
  }
}

output "ecr_repository_url" {
  description = "Repositorio donde se sube la imagen Docker"
  value       = aws_ecr_repository.app.repository_url
}

output "rds_endpoint" {
  description = "Host de PostgreSQL (solo accesible desde las EC2)"
  value       = aws_db_instance.postgres.address
}

output "target_group_arn" {
  value = aws_lb_target_group.app.arn
}
