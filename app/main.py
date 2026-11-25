"""Sistema de Registro de Notas Universitarias.

Aplicación FastAPI con vistas HTML (Jinja2) y una API JSON mínima.
Ruta de verificación para el ALB: GET /health
"""
import os
import socket
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

import models
from database import Base, db_ok, engine, get_db, wait_for_db

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
HOSTNAME = socket.gethostname()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Registro de Notas", version=APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals.update(
    hostname=HOSTNAME,
    version=APP_VERSION,
    pesos=models.PESOS_CORTE,
    aprobatoria=models.NOTA_APROBATORIA,
)


def redirigir(url: str, msg: str = "", error: str = "") -> RedirectResponse:
    if msg:
        url += f"?msg={quote(msg)}"
    elif error:
        url += f"?error={quote(error)}"
    return RedirectResponse(url, status_code=303)


def render(request: Request, plantilla: str, **ctx) -> HTMLResponse:
    ctx.update(msg=request.query_params.get("msg"), error=request.query_params.get("error"))
    return templates.TemplateResponse(request, plantilla, ctx)


# --------------------------------------------------------------------------- #
# Health checks
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    """Health check del ALB. No depende de la BD a propósito: si la BD cae,
    no queremos que el ALB saque de servicio TODAS las instancias a la vez."""
    return {"status": "ok", "host": HOSTNAME, "version": APP_VERSION}


@app.get("/health/db")
def health_db():
    ok = db_ok()
    return JSONResponse(
        {"database": "ok" if ok else "error", "host": HOSTNAME},
        status_code=200 if ok else 503,
    )


# --------------------------------------------------------------------------- #
# Vistas HTML
# --------------------------------------------------------------------------- #
@app.get("/", response_class=HTMLResponse)
def inicio(request: Request, db: Session = Depends(get_db)):
    stats = {
        "estudiantes": db.scalar(select(func.count(models.Estudiante.id))),
        "asignaturas": db.scalar(select(func.count(models.Asignatura.id))),
        "notas": db.scalar(select(func.count(models.Nota.id))),
    }
    recientes = db.scalars(
        select(models.Nota)
        .options(selectinload(models.Nota.estudiante), selectinload(models.Nota.asignatura))
        .order_by(models.Nota.id.desc())
        .limit(8)
    ).all()
    return render(request, "index.html", stats=stats, recientes=recientes)


# ---- Estudiantes ----------------------------------------------------------- #
@app.get("/estudiantes", response_class=HTMLResponse)
def listar_estudiantes(request: Request, db: Session = Depends(get_db)):
    estudiantes = db.scalars(select(models.Estudiante).order_by(models.Estudiante.nombre)).all()
    return render(request, "estudiantes.html", estudiantes=estudiantes)


@app.post("/estudiantes")
def crear_estudiante(
    codigo: str = Form(...),
    nombre: str = Form(...),
    programa: str = Form(...),
    db: Session = Depends(get_db),
):
    codigo, nombre, programa = codigo.strip(), nombre.strip(), programa.strip()
    if not (codigo and nombre and programa):
        return redirigir("/estudiantes", error="Todos los campos son obligatorios")
    db.add(models.Estudiante(codigo=codigo, nombre=nombre, programa=programa))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return redirigir("/estudiantes", error=f"Ya existe un estudiante con código {codigo}")
    return redirigir("/estudiantes", msg=f"Estudiante {nombre} registrado")


@app.post("/estudiantes/{estudiante_id}/eliminar")
def eliminar_estudiante(estudiante_id: int, db: Session = Depends(get_db)):
    est = db.get(models.Estudiante, estudiante_id)
    if est:
        db.delete(est)
        db.commit()
    return redirigir("/estudiantes", msg="Estudiante eliminado")


def reporte_estudiante(est: models.Estudiante) -> dict:
    """Agrupa las notas de un estudiante por asignatura y calcula definitivas."""
    por_asig: dict[int, dict] = {}
    for n in est.notas:
        fila = por_asig.setdefault(
            n.asignatura_id, {"asignatura": n.asignatura, "cortes": {}, "_notas": []}
        )
        fila["cortes"][n.corte] = float(n.valor)
        fila["_notas"].append(n)

    filas, suma_pond, creditos = [], 0.0, 0
    for fila in sorted(por_asig.values(), key=lambda f: f["asignatura"].nombre):
        fila["definitiva"] = models.definitiva(fila.pop("_notas"))
        if fila["definitiva"] is not None:
            suma_pond += fila["definitiva"] * fila["asignatura"].creditos
            creditos += fila["asignatura"].creditos
        filas.append(fila)
    promedio = round(suma_pond / creditos, 2) if creditos else None
    return {"filas": filas, "promedio": promedio}


@app.get("/estudiantes/{estudiante_id}", response_class=HTMLResponse)
def detalle_estudiante(estudiante_id: int, request: Request, db: Session = Depends(get_db)):
    est = db.scalar(
        select(models.Estudiante)
        .where(models.Estudiante.id == estudiante_id)
        .options(selectinload(models.Estudiante.notas).selectinload(models.Nota.asignatura))
    )
    if not est:
        raise HTTPException(404, "Estudiante no encontrado")
    return render(request, "estudiante_detalle.html", est=est, **reporte_estudiante(est))


# ---- Asignaturas ----------------------------------------------------------- #
@app.get("/asignaturas", response_class=HTMLResponse)
def listar_asignaturas(request: Request, db: Session = Depends(get_db)):
    asignaturas = db.scalars(select(models.Asignatura).order_by(models.Asignatura.nombre)).all()
    return render(request, "asignaturas.html", asignaturas=asignaturas)


@app.post("/asignaturas")
def crear_asignatura(
    codigo: str = Form(...),
    nombre: str = Form(...),
    creditos: int = Form(...),
    db: Session = Depends(get_db),
):
    codigo, nombre = codigo.strip(), nombre.strip()
    if not (codigo and nombre) or not 1 <= creditos <= 10:
        return redirigir("/asignaturas", error="Datos inválidos (créditos entre 1 y 10)")
    db.add(models.Asignatura(codigo=codigo, nombre=nombre, creditos=creditos))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return redirigir("/asignaturas", error=f"Ya existe una asignatura con código {codigo}")
    return redirigir("/asignaturas", msg=f"Asignatura {nombre} registrada")


@app.post("/asignaturas/{asignatura_id}/eliminar")
def eliminar_asignatura(asignatura_id: int, db: Session = Depends(get_db)):
    asig = db.get(models.Asignatura, asignatura_id)
    if asig:
        db.delete(asig)
        db.commit()
    return redirigir("/asignaturas", msg="Asignatura eliminada")


@app.get("/asignaturas/{asignatura_id}", response_class=HTMLResponse)
def detalle_asignatura(asignatura_id: int, request: Request, db: Session = Depends(get_db)):
    asig = db.scalar(
        select(models.Asignatura)
        .where(models.Asignatura.id == asignatura_id)
        .options(selectinload(models.Asignatura.notas).selectinload(models.Nota.estudiante))
    )
    if not asig:
        raise HTTPException(404, "Asignatura no encontrada")

    por_est: dict[int, dict] = {}
    for n in asig.notas:
        fila = por_est.setdefault(n.estudiante_id, {"estudiante": n.estudiante, "cortes": {}, "_n": []})
        fila["cortes"][n.corte] = float(n.valor)
        fila["_n"].append(n)
    filas = []
    for fila in sorted(por_est.values(), key=lambda f: f["estudiante"].nombre):
        fila["definitiva"] = models.definitiva(fila.pop("_n"))
        filas.append(fila)
    defs = [f["definitiva"] for f in filas if f["definitiva"] is not None]
    resumen = {
        "promedio": round(sum(defs) / len(defs), 2) if defs else None,
        "aprobados": sum(d >= models.NOTA_APROBATORIA for d in defs),
        "reprobados": sum(d < models.NOTA_APROBATORIA for d in defs),
    }
    return render(request, "asignatura_detalle.html", asig=asig, filas=filas, resumen=resumen)


# ---- Notas ----------------------------------------------------------------- #
@app.get("/notas", response_class=HTMLResponse)
def form_notas(request: Request, db: Session = Depends(get_db)):
    estudiantes = db.scalars(select(models.Estudiante).order_by(models.Estudiante.nombre)).all()
    asignaturas = db.scalars(select(models.Asignatura).order_by(models.Asignatura.nombre)).all()
    return render(request, "notas.html", estudiantes=estudiantes, asignaturas=asignaturas)


@app.post("/notas")
def registrar_nota(
    estudiante_id: int = Form(...),
    asignatura_id: int = Form(...),
    corte: int = Form(...),
    valor: float = Form(...),
    db: Session = Depends(get_db),
):
    if corte not in models.PESOS_CORTE:
        return redirigir("/notas", error="El corte debe ser 1, 2 o 3")
    if not 0.0 <= valor <= 5.0:
        return redirigir("/notas", error="La nota debe estar entre 0.0 y 5.0")
    if not db.get(models.Estudiante, estudiante_id) or not db.get(models.Asignatura, asignatura_id):
        return redirigir("/notas", error="Estudiante o asignatura no existe")

    valor = round(valor, 1)
    existente = db.scalar(
        select(models.Nota).where(
            models.Nota.estudiante_id == estudiante_id,
            models.Nota.asignatura_id == asignatura_id,
            models.Nota.corte == corte,
        )
    )
    if existente:
        existente.valor = valor
        accion = "actualizada"
    else:
        db.add(models.Nota(estudiante_id=estudiante_id, asignatura_id=asignatura_id, corte=corte, valor=valor))
        accion = "registrada"
    db.commit()
    return redirigir("/notas", msg=f"Nota {valor} del corte {corte} {accion}")


# --------------------------------------------------------------------------- #
# API JSON (útil para pruebas con curl en la demo)
# --------------------------------------------------------------------------- #
@app.get("/api/estudiantes")
def api_estudiantes(db: Session = Depends(get_db)):
    return [
        {"id": e.id, "codigo": e.codigo, "nombre": e.nombre, "programa": e.programa}
        for e in db.scalars(select(models.Estudiante).order_by(models.Estudiante.id))
    ]


@app.get("/api/asignaturas")
def api_asignaturas(db: Session = Depends(get_db)):
    return [
        {"id": a.id, "codigo": a.codigo, "nombre": a.nombre, "creditos": a.creditos}
        for a in db.scalars(select(models.Asignatura).order_by(models.Asignatura.id))
    ]


@app.get("/api/estudiantes/{estudiante_id}/reporte")
def api_reporte(estudiante_id: int, db: Session = Depends(get_db)):
    est = db.scalar(
        select(models.Estudiante)
        .where(models.Estudiante.id == estudiante_id)
        .options(selectinload(models.Estudiante.notas).selectinload(models.Nota.asignatura))
    )
    if not est:
        raise HTTPException(404, "Estudiante no encontrado")
    rep = reporte_estudiante(est)
    return {
        "estudiante": {"codigo": est.codigo, "nombre": est.nombre, "programa": est.programa},
        "promedio_ponderado": rep["promedio"],
        "asignaturas": [
            {
                "codigo": f["asignatura"].codigo,
                "nombre": f["asignatura"].nombre,
                "cortes": f["cortes"],
                "definitiva": f["definitiva"],
            }
            for f in rep["filas"]
        ],
        "servido_por": HOSTNAME,
    }
