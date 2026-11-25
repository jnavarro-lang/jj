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


def localizar_todos(codigo: str, tipo: str, referencia: str | None = None) -> list[Path]:
    """Como localizar(), pero con una URL/ruta explícita o TODOS los archivos de la carpeta."""
    if referencia:
        r = localizar(codigo, tipo, referencia)
        return [r] if r else []
    carpeta = config.INSUMOS_DIR / codigo
    if not carpeta.is_dir():
        return []
    return sorted(f for f in carpeta.iterdir()
                  if f.is_file() and tipo in norm(f.name) and not f.name.endswith(".ocr.txt"))


def texto(ruta: Path) -> str:
    suf = ruta.suffix.lower()
    if suf == ".pdf":
        ocr = ruta.with_suffix(".ocr.txt")  # texto OCR de un PDF escaneado, si existe al lado
        if ocr.exists():
            return ocr.read_text("utf8", "ignore")
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


def _codigo(valor: str, denominacion: str = "") -> str | None:
    """Código del empleo, corrigiendo confusiones típicas del OCR en códigos con letra
    (E1/G1 -> "El"/"Gl", G3 -> "63", O1 -> "01", T1 -> "Ti"/"Tí"/"T")."""
    v = valor.strip()
    v = re.sub(r"^([A-Z])[lIií|]\b", r"\g<1>1", v)
    v = re.sub(r"^6([1-9])\b", r"G\1", v)
    m = re.search(r"\b[A-Z]{0,3}\d{1,4}\b", v)
    cod = m.group(0) if m else None
    if cod and re.fullmatch(r"0\d", cod) and "asistencial" in norm(denominacion):
        cod = "O" + cod[1]
    if not cod and re.match(r"^T\b", v):
        cod = "T1"
    return cod


def _area(bloque: str) -> str | None:
    m = re.search(r"[ÁA]REA\s+FUNCIONAL\s*:?\s*\n?(.*?)(?=\n\s*(?:[IVX]+\.)|\Z)", bloque, flags=re.I | re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip(" :")[:200] or None


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
            denominacion=denom.split("  ")[0][:120].strip(" .,"),
            codigo=_codigo(_campo(bloque, r"c[oó]digo\b"), denom),
            grado=(re.search(r"\d{1,2}", _campo(bloque, r"\bgrado")) or [None])[0],
            nivel=nivel[:40] or None,
            numero_cargos=int(num.group()) if num else None,
            dependencia=_campo(bloque, r"\bdependencia")[:150] or None,
            area_funcional=_area(bloque),
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
