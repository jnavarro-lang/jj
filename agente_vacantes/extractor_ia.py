"""Extracción con Claude de empleos (manual de funciones) y dependencias (organigrama).

Se activa si hay credenciales de Anthropic (ANTHROPIC_API_KEY o perfil `ant auth login`).
Los PDF largos se parten en tramos de páginas para no exceder límites.
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import anthropic
from pypdf import PdfReader, PdfWriter

from . import config
from .documentos import EXT_IMAGEN
from .modelos import Empleo, ListaDependencias, ListaEmpleos

PAGINAS_POR_TRAMO = 30

PROMPT_MANUAL = (
    "Este es un tramo del Manual Específico de Funciones y Competencias Laborales (o del "
    "decreto de planta) de una entidad pública colombiana. Extrae cada empleo descrito con "
    "su identificación (denominación, código, grado, nivel, número de cargos, dependencia), "
    "propósito, funciones esenciales resumidas y requisitos de estudio y experiencia, "
    "incluidas alternativas/equivalencias. Copia los datos tal como aparecen; deja en null "
    "lo que el documento no diga. Si un empleo aparece cortado al inicio o al final del "
    "tramo, inclúyelo con lo que se vea."
)
PROMPT_ORGANIGRAMA = (
    "Este es el organigrama (o el decreto de estructura) de una entidad pública colombiana. "
    "Lista el nombre de todas las dependencias (despacho, secretarías, direcciones, "
    "subdirecciones, oficinas, grupos, etc.)."
)


def disponible() -> bool:
    """True si hay alguna credencial de Anthropic (clave, token o perfil de `ant auth login`)."""
    import os
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("ANTHROPIC_PROFILE"):
        return True
    return (Path.home() / ".config" / "anthropic").is_dir()


def _bloques(ruta: Path) -> list[dict]:
    suf = ruta.suffix.lower()
    if suf in EXT_IMAGEN:
        data = base64.standard_b64encode(ruta.read_bytes()).decode()
        return [{"type": "image", "source": {"type": "base64", "media_type": EXT_IMAGEN[suf], "data": data}}]
    if suf != ".pdf":
        from .documentos import texto
        return [{"type": "text", "text": texto(ruta)}]
    lector = PdfReader(str(ruta))
    bloques = []
    for ini in range(0, len(lector.pages), PAGINAS_POR_TRAMO):
        w = PdfWriter()
        for p in lector.pages[ini:ini + PAGINAS_POR_TRAMO]:
            w.add_page(p)
        buf = io.BytesIO()
        w.write(buf)
        data = base64.standard_b64encode(buf.getvalue()).decode()
        bloques.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}})
    return bloques


def _llamar(cliente: anthropic.Anthropic, bloque: dict, prompt: str, formato):
    kwargs = dict(
        model=config.CLAUDE_MODEL, max_tokens=16000,
        messages=[{"role": "user", "content": [bloque, {"type": "text", "text": prompt}]}],
        output_format=formato,
    )
    if config.CLAUDE_FALLBACKS:  # reenvío automático a otro modelo si hay rechazo
        kwargs["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        kwargs["extra_body"] = {"fallbacks": "default"}
    try:
        resp = cliente.messages.parse(**kwargs)
    except anthropic.BadRequestError as e:
        if "fallback" not in str(e).lower():
            raise
        kwargs.pop("extra_headers"), kwargs.pop("extra_body")
        resp = cliente.messages.parse(**kwargs)
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return None
    return resp.parsed_output


def extraer_empleos(ruta: Path) -> list[Empleo]:
    cliente = anthropic.Anthropic()
    vistos: dict[tuple, Empleo] = {}
    for bloque in _bloques(ruta):
        res = _llamar(cliente, bloque, PROMPT_MANUAL, ListaEmpleos)
        for e in (res.empleos if res else []):
            clave = (e.denominacion.lower().strip(), e.codigo, e.grado, (e.dependencia or "").lower())
            previo = vistos.get(clave)
            if previo is None:
                vistos[clave] = e
            else:  # completar campos vacíos con la otra mitad del empleo cortado
                for campo, valor in e.model_dump().items():
                    if valor and not getattr(previo, campo):
                        setattr(previo, campo, valor)
    return list(vistos.values())


def extraer_dependencias(ruta: Path) -> list[str]:
    cliente = anthropic.Anthropic()
    deps: list[str] = []
    for bloque in _bloques(ruta):
        res = _llamar(cliente, bloque, PROMPT_ORGANIGRAMA, ListaDependencias)
        for d in (res.dependencias if res else []):
            if d.lower() not in {x.lower() for x in deps}:
                deps.append(d)
    return deps
