# Terraform deja listo lo que Ansible necesita (sin secretos):
#  - ../ansible/inventory.ini          -> IPs de las EC2
#  - ../ansible/group_vars/all/infra.yml -> endpoint RDS, URL de ECR, región
resource "local_file" "inventario" {
  filename        = "${path.module}/../ansible/inventory.ini"
  file_permission = "0644"
  content = templatefile("${path.module}/templates/inventory.tftpl", {
    hosts    = [for i in aws_instance.app : { public_ip = i.public_ip, availability_zone = i.availability_zone }]
    ssh_user = var.ssh_user
    key_path = var.ssh_private_key_path
  })
}

resource "local_file" "infra_vars" {
  filename        = "${path.module}/../ansible/group_vars/all/infra.yml"
  file_permission = "0644"
  content = templatefile("${path.module}/templates/infra.yml.tftpl", {
    aws_region = var.aws_region
    ecr_repo   = aws_ecr_repository.app.repository_url
    db_host    = aws_db_instance.postgres.address
    db_port    = aws_db_instance.postgres.port
    db_name    = var.db_name
    db_user    = var.db_username
    app_port   = var.app_port
    vpc_cidr   = var.vpc_cidr
  })
}
