"""Lógica de cruce.

Opción 1 - Vacantes de planta: empleos del manual (plazas) vs. servidores en SIGEP.
Opción 2 - Contratos que se liberan: contratos con fecha fin en la ventana, ubicados en
la dependencia del organigrama y con un perfil inferido del objeto.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from .modelos import Empleo
from .sigep import norm

DEP_GENERICA = ("donde se ubique", "planta global", "donde se requiera", "todas las dependencias")


def _codigo_grado(cargo: str) -> tuple[str | None, str | None]:
    m = re.search(r"\b(\d{3,4})\s*[-–/ ]\s*(\d{1,2})\b", cargo or "")
    return (m.group(1), m.group(2).lstrip("0") or "0") if m else (None, None)


def _puntaje(empleo: Empleo, servidor: dict) -> float:
    cargo = servidor.get("cargo") or ""
    s = fuzz.token_set_ratio(norm(empleo.denominacion), norm(re.sub(r"[\d\-–/]+", " ", cargo)))
    if s < 88:
        return 0
    cod, gra = _codigo_grado(cargo)
    if cod and empleo.codigo and cod != str(empleo.codigo):
        return 0
    if gra and empleo.grado and gra != str(empleo.grado).lstrip("0"):
        return 0
    if cod and empleo.codigo:
        s += 10
    dep_e = norm(empleo.dependencia)
    if dep_e and not any(g in dep_e for g in DEP_GENERICA) and servidor.get("dependencia"):
        s += 5 if fuzz.token_set_ratio(dep_e, norm(servidor["dependencia"])) >= 85 else -5
    return s


def vacantes_planta(empleos: list[Empleo], servidores: list[dict]) -> tuple[list[dict], list[dict]]:
    """Devuelve (filas por empleo con ocupados/vacantes, alertas)."""
    pares = sorted(((_puntaje(e, s), i, j) for i, e in enumerate(empleos)
                    for j, s in enumerate(servidores)), reverse=True)
    plazas = [e.numero_cargos or 1 for e in empleos]
    ocupados: list[list[dict]] = [[] for _ in empleos]
    asignado: set[int] = set()
    for p, i, j in pares:
        if p <= 0:
            break
        if j in asignado or len(ocupados[i]) >= plazas[i]:
            continue
        ocupados[i].append(servidores[j])
        asignado.add(j)

    filas, alertas = [], []
    for i, e in enumerate(empleos):
        fila = e.model_dump()
        fila.update(plazas=plazas[i], ocupadas=len(ocupados[i]),
                    vacantes=max(0, plazas[i] - len(ocupados[i])),
                    ocupantes="; ".join(s.get("nombre", "") for s in ocupados[i]),
                    observacion="" if e.numero_cargos else
                    "El documento no indica el número de cargos; se asumió 1. Verifique con el decreto de planta.")
        filas.append(fila)
    for j, s in enumerate(servidores):
        if j not in asignado:
            alertas.append({"tipo": "Servidor sin empleo equivalente en el manual",
                            "detalle": f"{s.get('nombre', '')} - {s.get('cargo', '')} - {s.get('dependencia', '')}"})
    return filas, alertas


# ------------------------------------------------------------------ opción 2

NIVELES = [
    ("Profesional especializado", ("especializad", "especialista", "magister", "maestria")),
    ("Profesional", ("profesional", "abogad", "ingenier", "contador", "economista", "arquitect",
                     "psicolog", "trabajador social", "comunicador", "administrador", "medic")),
    ("Técnico / tecnólogo", ("tecnic", "tecnolog")),
    ("Asistencial / apoyo a la gestión", ("apoyo a la gestion", "asistencial", "auxiliar",
                                         "operativ", "conductor", "mensajer", "servicios generales")),
]
PROFESIONES = ("abogad", "ingenier", "contador", "economista", "arquitect", "psicolog",
               "trabajador social", "comunicador", "periodista", "administrador", "medic",
               "enfermer", "odontolog", "nutricion", "licenciad", "docente", "veterinari",
               "zootecnista", "agronom", "geolog", "biolog", "quimic", "estadistic", "sistemas")


def perfil_desde_objeto(objeto: str) -> dict:
    t = norm(objeto)
    nivel = next((n for n, claves in NIVELES if any(c in t for c in claves)), "No determinado")
    profesiones = sorted({p for p in PROFESIONES if p in t})
    return {"nivel_inferido": nivel, "formacion_mencionada": ", ".join(profesiones)}


def ubicar_dependencia(texto: str, dependencias: list[str]) -> tuple[str, int]:
    t = norm(texto)
    mejor, pm = "", 0
    for d in dependencias:
        p = fuzz.partial_ratio(norm(d), t)  # el nombre de la dependencia como frase dentro del objeto
        if (p > pm or (p == pm and len(d) > len(mejor))) and len(norm(d)) > 6:
            mejor, pm = d, p
    return (mejor, int(pm)) if pm >= 85 else ("", int(pm))


def empleo_relacionado(objeto: str, empleos: list[Empleo]) -> Empleo | None:
    t = norm(objeto)
    mejor, pm = None, 0
    for e in empleos:
        ref = norm(" ".join(x for x in (e.proposito, e.funciones) if x))
        if not ref:
            continue
        p = fuzz.token_set_ratio(t, ref)
        if p > pm:
            mejor, pm = e, p
    return mejor if pm >= 60 else None


def contratos_que_se_liberan(contratos: list[dict], dependencias: list[str],
                             empleos: list[Empleo]) -> list[dict]:
    vistos, filas = set(), []
    for c in contratos:
        nombre = c.get("contratista") or c.get("nombre") or ""
        clave = (norm(nombre), (c.get("fecha_fin") or "")[:10])
        if nombre and clave in vistos:
            continue
        vistos.add(clave)
        objeto = c.get("objeto") or c.get("descripcion") or c.get("cargo") or ""
        dep = c.get("dependencia") or ""
        confianza = 100 if dep else 0
        if not dep and dependencias:
            dep, confianza = ubicar_dependencia(objeto, dependencias)
        rel = empleo_relacionado(objeto, empleos) if empleos else None
        fila = {
            "fuente": c.get("fuente", "SIGEP"), "contratista": nombre,
            "numero_contrato": c.get("referencia") or c.get("numero_contrato") or c.get("id_contrato"),
            "objeto": objeto, "fecha_inicio": c.get("fecha_inicio"), "fecha_fin": c.get("fecha_fin"),
            "valor": c.get("valor"), "dependencia": dep, "confianza_dependencia": confianza,
            **perfil_desde_objeto(objeto),
            "empleo_de_referencia": f"{rel.denominacion} {rel.codigo or ''}-{rel.grado or ''}".strip() if rel else "",
            "requisitos_de_referencia": (rel.requisitos_estudio or "") if rel else "",
            "url": c.get("url") or c.get("detalle_url"),
        }
        filas.append(fila)
    return filas
