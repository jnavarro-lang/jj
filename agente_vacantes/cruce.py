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
TIPOS_PLANTA_EXCLUIDOS = ("contratista",)


def _mismo_empleo(a: str, b: str) -> bool:
    a, b = norm(a).strip(" ."), norm(b).strip(" .")
    if a == b:
        return True
    # tolera tildes/espacios/errores menores, pero no "presidente" vs "vicepresidente"
    return a.split()[:1] == b.split()[:1] and fuzz.token_sort_ratio(a, b) >= 95


def perfil_para(denominacion: str, codigo: str | None, grado: str | None, ubicacion: str,
                empleos: list[Empleo]) -> Empleo | None:
    """Ficha del manual más adecuada: misma denominación, código y grado; desempata por área."""
    cand = [e for e in empleos if _mismo_empleo(e.denominacion, denominacion)]
    if codigo:
        cand = [e for e in cand if not e.codigo or norm(e.codigo) == norm(codigo)] or cand
    if grado:
        cand = [e for e in cand if not e.grado or e.grado.lstrip("0") == grado.lstrip("0")] or []
    if not cand:
        return None
    u = norm(ubicacion)
    return max(cand, key=lambda e: fuzz.token_set_ratio(norm(" ".join(
        x for x in (e.area_funcional, e.dependencia) if x)), u) if u else 0)


def _perfil_cols(e: Empleo | None) -> dict:
    if not e:
        return {"ficha_manual": "No encontrada", "proposito": "", "requisitos": ""}
    req = " ".join(x for x in (e.requisitos_estudio, e.requisitos_experiencia) if x)
    if e.requisitos_estudio and e.requisitos_experiencia and e.requisitos_experiencia in e.requisitos_estudio:
        req = e.requisitos_estudio
    return {"ficha_manual": f"{e.denominacion} {e.codigo or ''}-{e.grado or ''} | {e.area_funcional or e.dependencia or ''}",
            "proposito": e.proposito or "", "requisitos": req}


def vacantes_planta(oficiales: list[dict], declaraciones: list[dict], empleos: list[Empleo]
                    ) -> tuple[list[dict], list[dict], list[dict]]:
    """Opción 1.

    Devuelve:
      detalle   - cada vacante del informe oficial, con el perfil de la ficha del manual
      balance   - por denominación: vacantes oficiales + retiros - ingresos posteriores al corte
      retiros   - declaraciones de RETIRO (cargos que pudieron quedar libres), con perfil
    """
    detalle = []
    for v in oficiales:
        e = perfil_para(v["denominacion"], v.get("codigo"), v.get("grado"),
                        f"{v.get('dependencia', '')} {v.get('grupo', '')}", empleos)
        detalle.append({**v, "fuente": "Informe oficial de planta", **_perfil_cols(e)})

    planta = [d for d in declaraciones if norm(d.get("cargo")) not in TIPOS_PLANTA_EXCLUIDOS]
    denominaciones: dict[str, str] = {}
    for x in [v["denominacion"] for v in oficiales] + [d["cargo"] for d in planta]:
        clave = next((k for k in denominaciones if _mismo_empleo(k, x)), None)
        denominaciones.setdefault(clave or x, x)

    balance = []
    for den in denominaciones:
        of = [v for v in oficiales if _mismo_empleo(v["denominacion"], den)]
        ret = [d for d in planta if d.get("tipo") == "RETIRO" and _mismo_empleo(d["cargo"], den)]
        ing = [d for d in planta if d.get("tipo") == "INGRESO" and _mismo_empleo(d["cargo"], den)]
        ing_personas = {norm(d["nombre"]) for d in ing}
        balance.append({
            "denominacion": den.title(),
            "vacantes_informe_oficial": len(of),
            "retiros_declarados": len(ret),
            "ingresos_declarados": len(ing_personas),
            "saldo_estimado": max(0, len(of) + len(ret) - len(ing_personas)),
            "grados_vacantes_oficiales": ", ".join(sorted({f"{v.get('codigo') or ''}-{v.get('grado') or ''}" for v in of})),
        })
    balance.sort(key=lambda b: -b["saldo_estimado"])

    retiros = []
    for d in sorted(planta, key=lambda d: d.get("fecha", ""), reverse=True):
        if d.get("tipo") != "RETIRO":
            continue
        fichas = [e for e in empleos if _mismo_empleo(e.denominacion, d["cargo"])]
        posterior = [i for i in planta if i.get("tipo") == "INGRESO" and _mismo_empleo(i["cargo"], d["cargo"])
                     and i.get("fecha", "") > d.get("fecha", "")]
        retiros.append({
            "cargo": d["cargo"], "fecha_retiro_declarado": d.get("fecha", "")[:10],
            "ingresos_posteriores_mismo_cargo": len(posterior),
            "grados_en_manual": ", ".join(sorted({f"{e.codigo or ''}-{e.grado or ''}" for e in fichas})),
            **_perfil_cols(fichas[0] if fichas else None),
        })
    return detalle, balance, retiros


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


def siglas_de(oficiales: list[dict]) -> dict[str, str]:
    """Siglas usadas por la entidad (p. ej. 'VPRE - GIT Riesgos' -> Vicepresidencia de Planeación...),
    tomando la dependencia más frecuente para cada sigla en el informe oficial."""
    from collections import Counter, defaultdict
    votos: dict[str, Counter] = defaultdict(Counter)
    for v in oficiales:
        sig = (v.get("grupo") or "").split(" - ")[0].strip()
        if 2 <= len(sig) <= 6 and sig.isupper() and v.get("dependencia"):
            votos[sig][v["dependencia"]] += 1
    return {s: c.most_common(1)[0][0] for s, c in votos.items()}


def ubicar_dependencia(texto: str, dependencias: list[str], siglas: dict[str, str] | None = None
                       ) -> tuple[str, int]:
    for sig, dep in (siglas or {}).items():
        if re.search(rf"\b{re.escape(sig)}\b", texto or ""):
            return dep, 70
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
                             empleos: list[Empleo], siglas: dict[str, str] | None = None) -> list[dict]:
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
        if not dep and (dependencias or siglas):
            dep, confianza = ubicar_dependencia(objeto, dependencias, siglas)
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
