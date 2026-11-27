# Evidencias del despliegue

Región `us-east-2` · URL de la demo: dirección del ALB (`terraform output alb_url`).

## 1. Terraform (infraestructura como código)
| Archivo | Qué demuestra |
|---|---|
| `01-terraform-plan.png` | `terraform plan` → *No changes*: la infraestructura real coincide con el código |
| `02-terraform-state-1.png`, `02-terraform-state-2.png` | `terraform state list`: 39 recursos creados por Terraform (red, SG, EC2, ALB, RDS, ECR, IAM) |
| `02-terraform-output.png` | Outputs: URL del ALB, EC2 en us-east-2a y us-east-2b, ECR y endpoint de RDS |

## 2. Recursos en AWS
| Archivo | Qué demuestra |
|---|---|
| `03-recursos-vpc.png` | Mapa de la VPC: 4 subredes (pública y privada por AZ), tablas de rutas pública/privada e IGW |
| `03-recursos-ec2.png` | 2 instancias en ejecución, una en cada zona de disponibilidad |
| `03-rds.png` | RDS PostgreSQL sin puerta de enlace a Internet y con 2 conexiones (las dos EC2) |
| `04-ecr-repositorio.png`, `04-ecr-imagen.png` | Imagen `1.0.0` en ECR, cifrada (AES-256), descargada por las EC2 con su rol IAM |

## 3. Ansible (automatización)
| Archivo | Qué demuestra |
|---|---|
| `06-idempotencia-1.png` … `06-idempotencia-4.png` | Segunda ejecución del playbook: `failed=0`, solo cambia el caché de apt (idempotencia) y verificación de `/health` y `/health/db` en ambas EC2 |

## 4. Alta disponibilidad y aplicación
| Archivo | Qué demuestra |
|---|---|
| `07-targets-healthy.png` | Target Group con los 2 destinos *Healthy* en AZ distintas |
| `08-app-balanceo-ip1.png`, `08-app-balanceo-ip2.png` | El ALB reparte las peticiones entre `ip-10-0-1-224` e `ip-10-0-2-144` |
| `08-app-estudiante.png` | Funcionalidad real desde la URL del ALB: notas por corte, definitiva y promedio ponderado |
| `08-app-asignatura-ip1.png`, `08-app-asignatura-ip2.png` | Mismos datos servidos por las dos EC2: base de datos compartida (RDS) |
| `09-fallo-target-group.png` | Prueba de fallo: contenedor de app1 detenido → *Unhealthy*; app2 sigue *Healthy* y atendiendo |
| `10-recuperacion-reboot.png` | Reinicio real de la EC2 app1 (`rebooted: true` en 33 s) |
| `10-recuperacion-docker.png` | Contenedor creado hace 2 días y *Up 3 minutes (healthy)*: arrancó solo tras el reinicio (`restart_policy: always`) |

## 5. Seguridad
| Archivo | Qué demuestra |
|---|---|
| `11-sg-lista.png` | Los 3 Security Groups del proyecto |
| `11-sg-alb.png` | ALB: solo HTTP 80 público |
| `11-sg-app.png` | EC2: 8000 solo desde el SG del ALB; SSH 22 solo desde la IP del administrador (/32) |
| `11-sg-db.png` | RDS: 5432 solo desde el SG de la app; sin reglas de salida |
| `12-hardening-ufw.png` | UFW activo: entrada denegada por defecto; 8000 solo desde la VPC |
| `12-hardening-fail2ban.png` | Fail2ban protegiendo SSH en ambas EC2 |
| `12-hardening-ssh.png` | SSH: sin root, sin contraseñas, `MaxAuthTries 3`, `AllowUsers ubuntu` |
| `12-hardening-contenedor.png` | Contenedor: usuario no root, sistema de archivos de solo lectura, `restart=always`, `CapDrop=ALL` |
