# Registro de Notas Universitarias — Proyecto Final

Aplicación web para registrar estudiantes, asignaturas y notas por corte, desplegada en AWS
con Docker, Terraform y Ansible detrás de un Application Load Balancer.

> Estado: **Fase 1 completa (aplicación + Docker)**. Terraform, Ansible, diagrama y evidencias en progreso.

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
_Pendiente (Fase 3)._

## 4. Ansible
_Pendiente (Fase 4)._

## 5. Diagrama de arquitectura
_Pendiente._

## 6. Evidencias
_Pendiente._

## 7. Seguridad y decisiones técnicas
- La BD es compartida (PostgreSQL/RDS) para que ambas instancias muestren los mismos datos.
- El contenedor corre sin privilegios de root.
- Los secretos se pasan por variables de entorno; `.env`, `*.pem`, `*.tfstate` y `terraform.tfvars` están en `.gitignore`.

## 8. Uso de IA
Se usó Claude (Anthropic) como apoyo para estructurar el plan del proyecto y generar el código base
de la aplicación, que fue revisado, probado y adaptado por el autor.
