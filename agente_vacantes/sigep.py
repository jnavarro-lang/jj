"""Consulta ciudadana del SIGEP (directorio de servidores públicos y contratistas).

El parser es deliberadamente genérico: busca el formulario, sus <select> y la tabla de
resultados por palabras clave en los encabezados, porque la estructura exacta del HTML
puede cambiar. Si algo no se reconoce, se guarda el HTML en .cache/sigep_debug/ para
ajustar el parser.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from . import config, http

# encabezado normalizado -> campo estándar
COLUMNAS = {
    "nombre": ("nombre", "nombres", "servidor", "contratista"),
    "cargo": ("cargo", "empleo", "denominacion"),
    "objeto": ("objeto",),
    "dependencia": ("dependencia", "area", "unidad"),
    "entidad": ("entidad", "institucion"),
    "fecha_inicio": ("fecha inicio", "fecha de inicio", "inicio", "fecha vinculacion"),
    "fecha_fin": ("fecha fin", "fecha finalizacion", "fecha de finalizacion", "terminacion"),
    "correo": ("correo", "email"),
    "telefono": ("telefono",),
    "numero_contrato": ("contrato", "numero de contrato"),
    "valor": ("valor", "honorarios"),
}


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


# Encabezados reales de la Consulta Ciudadana Ley 2013 de 2019 (verificados en noviembre 2026).
ENCABEZADOS_EXACTOS = {
    "declarante": "declarante",
    "descargar": "descargar",
    "entidad": "entidad",
    "cargo/contratista": "cargo",
    "tipo de publicacion": "tipo_publicacion",
    "declaracion no.": "numero_declaracion",
    "declaracion no": "numero_declaracion",
    "fecha de publicacion": "fecha_publicacion",
    "estado declaracion": "estado_declaracion",
}
TIPOS_DOCUMENTO = ("CEDULA DE CIUDADANIA", "CEDULA DE EXTRANJERIA", "PASAPORTE", "TARJETA DE IDENTIDAD",
                   "NIT", "PERMISO", "REGISTRO CIVIL", "DOCUMENTO")


def separar_declarante(texto: str) -> dict:
    """'NOMBRE CEDULA DE CIUDADANIA - 123' -> nombre, tipo_documento, numero_documento."""
    t = re.sub(r"\s+", " ", texto or "").strip()
    m = re.match(r"^(.*?)\s*-\s*([\w.]+)$", t)
    cuerpo, numero = (m.group(1), m.group(2)) if m else (t, "")
    sin_tildes = unicodedata.normalize("NFKD", cuerpo).encode("ascii", "ignore").decode().upper()
    pos = [sin_tildes.find(" " + d) for d in TIPOS_DOCUMENTO if sin_tildes.find(" " + d) >= 0]
    if pos:
        corte = min(pos)
        return {"nombre": cuerpo[:corte].strip(), "tipo_documento": cuerpo[corte:].strip(),
                "numero_documento": numero}
    return {"nombre": cuerpo.strip(), "tipo_documento": "", "numero_documento": numero}


def _campo_para(encabezado: str) -> str | None:
    h = norm(encabezado)
    if h in ENCABEZADOS_EXACTOS:
        return ENCABEZADOS_EXACTOS[h]
    # Coincidencia más específica primero (fecha fin antes que "fin" genérico, etc.)
    for campo, claves in sorted(COLUMNAS.items(), key=lambda kv: -max(len(c) for c in kv[1])):
        if any(c in h for c in claves):
            return campo
    return None


def parsear_resultados(html: str | bytes, base_url: str = config.SIGEP_BASE) -> list[dict]:
    """Extrae las filas de la tabla de resultados (la tabla con más filas útiles)."""
    soup = BeautifulSoup(html, "lxml")
    mejor: list[dict] = []
    for tabla in soup.find_all("table"):
        filas = tabla.find_all("tr")
        if len(filas) < 2:
            continue
        cab = filas[0].find_all(["th", "td"])
        campos = [_campo_para(c.get_text(" ", strip=True)) or f"col{i}" for i, c in enumerate(cab)]
        registros = []
        for tr in filas[1:]:
            celdas = tr.find_all("td")
            if not celdas:
                continue
            reg = {}
            for i, td in enumerate(celdas):
                clave = campos[i] if i < len(campos) else f"col{i}"
                reg[clave] = td.get_text(" ", strip=True)
                a = td.find("a", href=True)
                if a and "detalle_url" not in reg:
                    reg["detalle_url"] = urljoin(base_url, a["href"])
            if any(v for k, v in reg.items() if k != "detalle_url"):
                if "declarante" in reg:
                    reg.update(separar_declarante(reg.pop("declarante")))
                reg.pop("descargar", None)
                if "cargo" in reg:
                    reg["es_contratista"] = norm(reg["cargo"]) == "contratista"
                registros.append(reg)
        utiles = sum(1 for c in campos if not c.startswith("col"))
        if utiles and len(registros) > len(mejor):
            mejor = registros
    return mejor


def siguiente_pagina(html: str | bytes, base_url: str = config.SIGEP_BASE) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        txt = norm(a.get_text())
        clases = " ".join(a.get("class", []))
        if "nextlink" in clases.lower() or txt in ("siguiente", "next", ">", ">>", "»"):
            return urljoin(base_url, a["href"])
    return None


def total_resultados(html: str | bytes) -> int | None:
    texto = norm(BeautifulSoup(html, "lxml").get_text(" "))
    m = re.search(r"(\d[\d.,]*)\s+(resultados|registros|declaraciones encontradas)", texto)
    return int(re.sub(r"[.,]", "", m.group(1))) if m else None


def con_tamano_pagina(url: str, tamano: int) -> str:
    """Cambia max=… en un enlace de paginación para traer más filas por página."""
    p = urlparse(url)
    q = {k: v[0] for k, v in parse_qs(p.query, keep_blank_values=True).items()}
    if "max" in q:
        q["max"] = str(tamano)
    from urllib.parse import urlencode
    return p._replace(query=urlencode(q)).geturl()


# ------------------------------------------------------------------ consultas en vivo

def formulario() -> bytes:
    return http.get(config.SIGEP_BASE, navegador=True)


def listar_entidades() -> list[Opcion]:
    """Todas las opciones de 'Nombre entidad'. Con Chrome abre la lista como una persona."""
    from . import navegador
    if navegador.disponible():
        opciones = navegador.listar_entidades(config.SIGEP_BASE)
        if opciones:
            return [Opcion(v, e) for v, e in opciones]
    return opciones_select(formulario(), "entidad")


def tipos_persona() -> dict[str, str]:
    """{'natural': '25', 'juridica': '26'} leído del formulario (o de SIGEP_TIPOS)."""
    if config.SIGEP_TIPOS:
        return {f"tipo{v}": v for v in config.SIGEP_TIPOS.split(",") if v.strip()}
    tipos = {}
    for o in opciones_select(formulario(), "tipoPersonaId"):
        e = norm(o.etiqueta)
        tipos["juridica" if "jurid" in e else "natural" if "natural" in e else e] = o.valor
    return tipos or {"natural": "25", "juridica": "26"}


def consultar(entidad: str, tipo_persona: str, fecha_desde: str = "", fecha_hasta: str = "",
              max_paginas: int = 500, nombre: str = "") -> list[dict]:
    """Consulta todas las páginas de resultados. Fechas en formato dd/mm/aaaa."""
    from . import navegador
    if navegador.disponible() and config.SIGEP_MODO == "formulario":
        paginas = navegador.buscar_en_formulario(config.SIGEP_BASE, tipo_persona, entidad, nombre,
                                                 fecha_desde, fecha_hasta, max_paginas)
        if paginas is not None:
            return _filas_de_paginas(paginas, entidad, tipo_persona)
    params = {
        "tipoPersonaId": tipo_persona, "tipoDeclaracionId": "", "razonSocial": "",
        "primerNombre": "", "segundoNombre": "",
        "primerApellido": "", "segundoApellido": "", "numeroDocumento": "",
        "entidad": entidad, "fechaFinalizacionDesde": fecha_desde,
        "fechaFinalizacionHasta": fecha_hasta, "find": "Find",
        "max": config.SIGEP_PAGE_SIZE, "offset": 0,
    }
    url = config.SIGEP_BASE
    todos: list[dict] = []
    vistos: set[tuple] = set()
    for _ in range(max_paginas):
        html = http.get(url, params=params, navegador=True)
        filas = parsear_resultados(html, url)
        nuevas = [f for f in filas if tuple(sorted(f.items())) not in vistos]
        if not nuevas:
            if not todos:
                _debug(entidad, tipo_persona, html)
            break
        for f in nuevas:
            vistos.add(tuple(sorted(f.items())))
            f["entidad_codigo"] = entidad
            todos.append(f)
        sig = siguiente_pagina(html, url)
        if sig:  # el enlace ya trae sus propios parámetros
            sig = con_tamano_pagina(sig, config.SIGEP_PAGE_SIZE)
            parsed = urlparse(sig)
            url = sig.split("?")[0]
            params = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
        else:
            break  # sin enlace "siguiente" no hay más páginas
    return todos


def ultimos_servidores_activos(declaraciones: list[dict]) -> list[dict]:
    """Servidores (no contratistas) cuya última declaración no es de RETIRO."""
    ultima: dict[str, dict] = {}
    for d in declaraciones:
        if d.get("es_contratista"):
            continue
        clave = d.get("numero_documento") or norm(d.get("nombre"))
        if clave not in ultima or (d.get("fecha_publicacion") or "") > (ultima[clave].get("fecha_publicacion") or ""):
            ultima[clave] = d
    return [d for d in ultima.values() if "retiro" not in norm(d.get("tipo_publicacion"))]


def _filas_de_paginas(paginas: list[bytes], entidad: str, tipo: str) -> list[dict]:
    todos, vistos = [], set()
    for html in paginas:
        for f in parsear_resultados(html):
            clave = tuple(sorted(f.items()))
            if clave not in vistos:
                vistos.add(clave)
                f["entidad_codigo"] = entidad
                todos.append(f)
    if not todos and paginas:
        _debug(entidad, tipo, paginas[0])
    return todos


def _debug(entidad: str, tipo: str, html: bytes) -> None:
    d = config.CACHE_DIR / "sigep_debug"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{entidad}_{tipo}.html").write_bytes(html)
