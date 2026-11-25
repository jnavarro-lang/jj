"""Consulta ciudadana de Función Pública: declaraciones Ley 2013 de 2019.

https://www1.funcionpublica.gov.co/fdci/consultaCiudadana/index

Estructura real (verificada en noviembre de 2026):
* Formulario GET con tipoPersonaId (25 = NATURAL, 26 = JURÍDICA), entidad (código,
  ~14.800 opciones), nombres, documento y fechaFinalizacionDesde/Hasta (dd/mm/aaaa).
  OJO: esa fecha es la de PUBLICACIÓN de la declaración, no la de fin de un contrato.
* Tabla de resultados: Declarante | Descargar | Entidad | Cargo/Contratista |
  Tipo de publicación (INGRESO, RETIRO, PERIÓDICO, OTRO) | Declaración No. |
  Fecha de publicación | Estado declaración.
* Paginación Grails: find=FindNext + offset + max (acepta max=100), enlace a.nextLink.

Una declaración de RETIRO indica que alguien dejó el cargo; una de INGRESO, que alguien
lo ocupó. Con eso se estiman movimientos de planta por cargo.
No se guarda el número de documento de los declarantes.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from bs4 import BeautifulSoup

from . import config, http

TIPO_NATURAL = "25"
TIPO_JURIDICA = "26"


def norm(txt: str | None) -> str:
    txt = unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", txt).strip().lower()


@dataclass
class Opcion:
    valor: str
    etiqueta: str


def opciones_select(html: str | bytes, nombre: str) -> list[Opcion]:
    soup = BeautifulSoup(html, "lxml")
    sel = soup.find("select", attrs={"name": nombre}) or soup.find("select", id=nombre)
    if not sel:
        return []
    return [Opcion(o.get("value", "").strip(), o.get_text(" ", strip=True))
            for o in sel.find_all("option") if o.get("value", "").strip()]


_COLUMNAS = {
    "declarante": "nombre", "entidad": "entidad", "cargo": "cargo",
    "tipo de publicacion": "tipo", "declaracion no": "declaracion",
    "fecha de publicacion": "fecha", "estado": "estado",
}


def parsear_declaraciones(html: str | bytes) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    tabla = soup.find("table", class_="table")
    if not tabla:
        return []
    filas = tabla.find_all("tr")
    cab = [norm(c.get_text(" ", strip=True)) for c in filas[0].find_all(["th", "td"])]
    campos = []
    for c in cab:
        campos.append(next((v for k, v in _COLUMNAS.items() if c.startswith(k)), None))
    salida = []
    for tr in filas[1:]:
        celdas = tr.find_all("td")
        if len(celdas) < 5:
            continue
        reg = {}
        for campo, td in zip(campos, celdas):
            if not campo:
                continue
            if campo == "nombre":  # primer <p> = nombre; el segundo trae el documento (no se guarda)
                p = td.find("p")
                reg[campo] = (p or td).get_text(" ", strip=True)
            else:
                reg[campo] = td.get_text(" ", strip=True)
        reg["tipo"] = reg.get("tipo", "").upper()
        salida.append(reg)
    return salida


def hay_siguiente(html: str | bytes) -> bool:
    return BeautifulSoup(html, "lxml").find("a", class_="nextLink") is not None


def formulario() -> bytes:
    return http.get(config.SIGEP_BASE)


def listar_entidades() -> list[Opcion]:
    return opciones_select(formulario(), "entidad")


def declaraciones(entidad: str, desde: str, hasta: str, tipo_persona: str = TIPO_NATURAL,
                  max_paginas: int = 2000) -> list[dict]:
    """Todas las declaraciones publicadas entre `desde` y `hasta` (dd/mm/aaaa).

    entidad="" consulta todas las entidades a la vez.
    """
    params = {
        "find": "FindNext", "tipoPersonaId": tipo_persona, "tipoDeclaracionId": "",
        "razonSocial": "", "primerApellido": "", "primerNombre": "", "segundoApellido": "",
        "segundoNombre": "", "numeroDocumento": "", "entidad": entidad,
        "fechaFinalizacionDesde": desde, "fechaFinalizacionHasta": hasta,
        "offset": 0, "max": config.SIGEP_PAGE_SIZE, "sort": "FECHA_FINALIZACION", "order": "desc",
    }
    todas: list[dict] = []
    for _ in range(max_paginas):
        html = http.get(config.SIGEP_BASE, params=params)
        filas = parsear_declaraciones(html)
        for f in filas:
            f["entidad_codigo"] = entidad
        todas.extend(filas)
        if not filas or not hay_siguiente(html):
            break
        params["offset"] += params["max"]
    if not todas:
        _debug(entidad, html)
    return todas


def _debug(entidad: str, html: bytes) -> None:
    d = config.CACHE_DIR / "sigep_debug"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{entidad or 'todas'}.html").write_bytes(html)
