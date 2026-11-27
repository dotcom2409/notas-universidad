# Registro de Notas Universitarias — Proyecto Final

Aplicación web para registrar estudiantes, asignaturas y notas por corte, desplegada en AWS
con Docker, Terraform y Ansible detrás de un Application Load Balancer.

> Estado: **App, Docker, Terraform y Ansible listos**. Diagrama y evidencias en progreso.

## 1. Descripción de la aplicación

- **Propósito:** llevar el registro académico de notas de una universidad.
- **Funcionalidad:**
  - CRUD de estudiantes (código, nombre, programa) y asignaturas (código, nombre, créditos).
  - Registro de notas por corte (escala 0.0 – 5.0). Si la nota del corte ya existe, se actualiza.
  - Nota definitiva ponderada: Corte 1 (30 %) + Corte 2 (30 %) + Corte 3 (40 %). Aprueba con ≥ 3.0.
  - Promedio ponderado por créditos de cada estudiante; promedio, aprobados y reprobados por asignatura.
  - El pie de página muestra el **hostname** del contenedor que respondió (evidencia del balanceo del ALB).
- **Origen:** aplicación nueva desarrollada para el proyecto.
- **Stack:** Python 3.12, FastAPI, Jinja2, SQLAlchemy 2, PostgreSQL 16 (RDS en AWS).

### Rutas principales

| Ruta | Descripción |
|---|---|
| `GET /` | Panel con totales y últimas notas |
| `GET/POST /estudiantes` | Listar / crear estudiantes |
| `GET /estudiantes/{id}` | Notas, definitivas y promedio del estudiante |
| `GET/POST /asignaturas` | Listar / crear asignaturas |
| `GET /asignaturas/{id}` | Notas del curso, promedio, aprobados/reprobados |
| `GET/POST /notas` | Registrar o actualizar nota |
| `GET /api/estudiantes`, `/api/asignaturas` | API JSON |
| `GET /api/estudiantes/{id}/reporte` | Reporte JSON (incluye `servido_por`) |
| `GET /health` | **Health check del ALB** (no depende de la BD) |
| `GET /health/db` | Verifica conexión a la BD (503 si falla) |

> `/health` no consulta la base de datos a propósito: si RDS fallara, el ALB no debe sacar de servicio
> todas las instancias a la vez. El estado de la BD se revisa aparte en `/health/db`.

## 2. Código y Docker

```
app/
├── main.py            # rutas y lógica
├── models.py          # tablas y cálculo de definitivas
├── database.py        # conexión (variables de entorno)
├── templates/         # vistas HTML
├── static/style.css
├── requirements.txt
└── Dockerfile
docker-compose.yml     # entorno local: app + PostgreSQL
.env.example           # variables documentadas (sin secretos reales)
```

**Buenas prácticas del Dockerfile:** imagen oficial `python:3.12-slim`, dependencias con versión fija,
ejecución con usuario **no root** (`app`), `HEALTHCHECK` integrado y `.dockerignore` para no copiar secretos.

### Variables de configuración

| Variable | Descripción | Ejemplo |
|---|---|---|
| `APP_PORT` | Puerto interno de la app | `8000` |
| `APP_VERSION` | Versión mostrada en el pie | `1.0.0` |
| `DB_HOST` | Host de PostgreSQL (vacío = SQLite local de desarrollo) | endpoint de RDS |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_NAME` | Base de datos | `notas` |
| `DB_USER` | Usuario de la BD | `notas_app` |
| `DB_PASSWORD` | Contraseña (**nunca en Git**) | — |

### Ejecución local

```bash
cp .env.example .env          # edita DB_PASSWORD
docker compose up -d --build
# Abrir http://localhost:8000  ·  verificar: curl localhost:8000/health
docker compose down           # (agrega -v para borrar los datos)
```

Sin Docker (desarrollo rápido con SQLite):

```bash
cd app && pip install -r requirements.txt && uvicorn main:app --reload
```

## 3. Terraform

Región: `us-east-2`. Toda la infraestructura se crea con Terraform (`terraform/`):

| Archivo | Recursos |
|---|---|
| `network.tf` | VPC `10.0.0.0/16`, 2 subredes públicas y 2 privadas en 2 AZ, Internet Gateway, tablas de rutas |
| `security.tf` | SG del ALB (80 público), SG de la app (8000 solo desde el ALB, 22 solo desde `admin_cidr`), SG de la BD (5432 solo desde la app) |
| `iam.tf` | Rol de EC2 con mínimo privilegio: ECR solo lectura + SSM |
| `ecr.tf` | Repositorio de imágenes con escaneo de vulnerabilidades |
| `compute.tf` | 2 EC2 Ubuntu 24.04, una por AZ, IMDSv2 obligatorio, disco cifrado |
| `alb.tf` | ALB, Target Group con health check `/health`, listener HTTP 80 |
| `rds.tf` | PostgreSQL 16 en subredes privadas, cifrado, sin acceso público |
| `ansible.tf` | Genera `ansible/inventory.ini` y `ansible/group_vars/all/infra.yml` |
| `outputs.tf` | URL del ALB, IPs de las EC2, URL de ECR, endpoint de RDS |

**Cómo se relacionan:** la VPC contiene las subredes; las públicas salen a Internet por el IGW y alojan el ALB
y las EC2; las privadas alojan RDS sin ruta a Internet. El ALB reenvía al Target Group, que registra las 2 EC2
y las revisa con `/health`. Los SG se referencian entre sí (ALB → app → BD) en lugar de usar rangos de IP.

**State:** se guarda localmente en `terraform/terraform.tfstate`, excluido de Git porque contiene datos
sensibles (p. ej. la contraseña de RDS). En producción se usaría un backend S3 cifrado con bloqueo.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # completar
terraform init
terraform fmt && terraform validate
terraform plan -out plan.tfplan
terraform apply plan.tfplan
terraform output
terraform destroy                              # al terminar, para evitar costos
```

## 4. Ansible

Se ejecuta desde **WSL (Ubuntu)**. Terraform crea los recursos AWS; Ansible configura los servidores y despliega.

| Rol | Qué hace |
|---|---|
| `common` | Paquetes base, zona horaria, usuario de sistema `notas` (sin shell) y directorio `/opt/notas` |
| `hardening` | SSH sin root ni contraseña · UFW (deny por defecto) · Fail2ban · parches automáticos |
| `docker` | Docker + `amazon-ecr-credential-helper` (autenticación a ECR con el rol IAM, sin claves) |
| `deploy` | Genera `app.env` (0600), descarga la imagen de ECR, ejecuta el contenedor con `restart_policy: always` y verifica `/health` y `/health/db` |

- **Inventario y variables:** Terraform genera `inventory.ini` y `group_vars/all/infra.yml`. Las variables propias
  están en `group_vars/all/main.yml` y la contraseña de BD en `vault.yml`, cifrado con **Ansible Vault** (fuera de Git).
- **Reinicio automático:** el servicio Docker está habilitado al arranque y el contenedor usa `restart_policy: always`.
- **Idempotencia:** una segunda ejecución no hace cambios.

```bash
# En WSL
cd /mnt/c/proyectos/notas-universidad/ansible
cp group_vars/all/vault.yml.example group_vars/all/vault.yml   # misma clave de RDS
ansible-vault encrypt group_vars/all/vault.yml
./deploy.sh
```

## 5. Diagrama de arquitectura
_Pendiente._

## 6. Evidencias
_Pendiente._

## 7. Seguridad y decisiones técnicas

**Red**
- Único punto público: el ALB (puerto 80). Las EC2 aceptan el puerto 8000 **solo desde el SG del ALB**.
- SSH (22) solo desde la IP del administrador (`admin_cidr`, validado para que nunca sea `0.0.0.0/0`).
- RDS en subredes privadas sin ruta a Internet, `publicly_accessible = false`, solo accesible desde el SG de la app.

**Linux (hardening con Ansible)**
1. SSH: sin login de root, sin contraseñas (solo llave), `MaxAuthTries 3`, `AllowUsers ubuntu`.
2. UFW: entrada denegada por defecto; solo 22 y 8000 (este último solo desde la VPC).
3. Fail2ban protegiendo SSH.
4. Actualizaciones automáticas de seguridad.

**Credenciales e IAM**
- Rol de EC2 con mínimo privilegio: ECR solo lectura + SSM. Las EC2 no guardan claves de AWS.
- IMDSv2 obligatorio. Discos EBS y RDS cifrados.
- Contraseña de BD: variable `sensitive` en Terraform y Ansible Vault. `.env`, `*.pem`, `*.tfstate`,
  `terraform.tfvars`, `inventory.ini` y `vault.yml` están en `.gitignore`.

**Contenedores**
- Imagen oficial `python:3.12-slim`, escaneo de vulnerabilidades en ECR, usuario no root.
- Contenedor `read_only`, `cap_drop: ALL`, `no-new-privileges`, logs con rotación.
- `network_mode: host` para que UFW filtre el puerto (Docker con puertos publicados se salta UFW) y para que
  la app muestre el hostname de la EC2 que respondió.

**Decisiones y limitaciones**
- `/health` no depende de la BD: si RDS falla, el ALB no saca de servicio ambas instancias a la vez.
- **HTTP sin HTTPS:** el proyecto no usa dominio propio. En producción: dominio en Route 53, certificado ACM,
  listener 443 y redirección 80 → 443.
- **RDS Single-AZ** por costo: es un punto único de fallo de la BD. Mejora: `db_multi_az = true`.
- EC2 en subredes públicas (con SG restrictivo) para evitar el costo de NAT Gateway. Mejora: subredes privadas + NAT + Session Manager.
- State de Terraform local. Mejora: backend S3 cifrado con bloqueo.
- Usuario IAM `terraform-admin` con `AdministratorAccess` para aprovisionar; en producción, permisos acotados.

## 8. Uso de IA
Se usó Claude (Anthropic) como apoyo para estructurar el plan del proyecto y generar el código base
de la aplicación, que fue revisado, probado y adaptado por el autor.
