"""Localiza, descarga y lee los documentos de cada entidad (manual, organigrama, planta).

Fuentes, en orden: columna del entidades.csv (ruta local o URL) y luego la carpeta
insumos/<codigo_entidad>/ con archivos cuyo nombre contenga "manual", "organigrama"
o "planta".
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import pdfplumber

from . import config, http
from .modelos import Empleo
from .sigep import norm

TIPOS = ("manual", "organigrama", "planta")
EXT_IMAGEN = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def localizar(codigo: str, tipo: str, referencia: str | None = None) -> Path | None:
    if referencia:
        referencia = referencia.strip()
        if referencia.lower().startswith(("http://", "https://")):
            nombre = Path(urlparse(referencia).path).name or f"{tipo}.pdf"
            destino = config.INSUMOS_DIR / codigo / f"{tipo}_{nombre}"
            if not destino.exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(http.get(referencia, timeout=180))
            return destino
        p = Path(referencia)
        if p.exists():
            return p
    carpeta = config.INSUMOS_DIR / codigo
    if carpeta.is_dir():
        candidatos = sorted(f for f in carpeta.iterdir() if f.is_file() and tipo in norm(f.name))
        if candidatos:
            return candidatos[0]
    return None


def texto(ruta: Path) -> str:
    suf = ruta.suffix.lower()
    if suf == ".pdf":
        with pdfplumber.open(ruta) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if suf == ".docx":
        with zipfile.ZipFile(ruta) as z:
            xml = z.read("word/document.xml").decode("utf8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        return re.sub(r"<[^>]+>", "", xml)
    if suf in (".txt", ".md", ".csv"):
        return ruta.read_text("utf8", "ignore")
    return ""


# ------------------------------------------------- extractor heurístico (sin IA)

_SECCION = r"(?:\n\s*(?:[IVX]+\.|[0-9]+\.)\s+[A-ZÁÉÍÓÚÑ ]{6,}\n)"


def _campo(bloque: str, *etiquetas: str) -> str:
    for et in etiquetas:
        m = re.search(et + r"\s*[:\-]?\s*(.+)", bloque, flags=re.I)
        if m:
            return m.group(1).strip()
    return ""


def _seccion(bloque: str, titulo: str) -> str:
    m = re.search(titulo + r"[^\n]*\n(.*?)(?=" + _SECCION + r"|\Z)", bloque, flags=re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def empleos_heuristico(txt: str) -> list[Empleo]:
    """Parser para el formato típico de manual (Decreto 1083 de 2015 / Guía DAFP)."""
    partes = re.split(r"(?=denominaci[oó]n\s+del\s+empleo)", txt, flags=re.I)
    empleos = []
    for i in range(1, len(partes)):
        bloque, previo = partes[i], partes[i - 1][-400:]
        denom = _campo(bloque, r"denominaci[oó]n\s+del\s+empleo")
        if not denom:
            continue
        nivel = _campo(previo, r"\bnivel\b") or _campo(bloque.split("\n", 3)[-1][:300], r"\bnivel\b")
        cargos = _campo(bloque, r"n[uú]mero\s+de\s+cargos", r"no\.?\s+de\s+cargos", r"n[°º]\s*de\s+cargos")
        num = re.search(r"\d+", cargos)
        estudio = _seccion(bloque, r"formaci[oó]n\s+acad[eé]mica") or _seccion(bloque, r"estudios?")
        exper = _seccion(bloque, r"\bexperiencia\b")
        req = _seccion(bloque, r"requisitos")
        empleos.append(Empleo(
            denominacion=denom.split("  ")[0][:120],
            codigo=(re.search(r"\d{3,4}", _campo(bloque, r"c[oó]digo")) or [None])[0],
            grado=(re.search(r"\d{1,2}", _campo(bloque, r"\bgrado")) or [None])[0],
            nivel=nivel[:40] or None,
            numero_cargos=int(num.group()) if num else None,
            dependencia=_campo(bloque, r"\bdependencia")[:150] or None,
            proposito=_seccion(bloque, r"prop[oó]sito\s+principal")[:1500] or None,
            funciones=_seccion(bloque, r"funciones\s+esenciales")[:3000] or None,
            requisitos_estudio=(estudio or req)[:1500] or None,
            requisitos_experiencia=exper[:800] or None,
        ))
    return empleos


def dependencias_heuristico(txt: str) -> list[str]:
    claves = ("despacho", "secretar", "direcci", "subdirecci", "oficina", "grupo",
              "gerencia", "jefatura", "coordinaci", "division", "unidad", "control interno")
    vistos, salida = set(), []
    for linea in txt.splitlines():
        l = linea.strip(" -•\t")
        if 4 < len(l) < 120 and any(c in norm(l) for c in claves) and norm(l) not in vistos:
            vistos.add(norm(l))
            salida.append(l)
    return salida
