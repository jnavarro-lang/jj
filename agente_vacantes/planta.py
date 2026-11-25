"""Lee el informe oficial de planta de personal / cargos sin proveer que publican las entidades
(sección Transparencia > Talento humano). Ejemplo: ANI, "Informe planta de personal 30/06/2025",
con la tabla Naturaleza | Vacancia | Den-cod-g | Dependencia | GIT-Equipo.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pdfplumber

from .sigep import norm

_DCG = re.compile(r"(?P<den>.+?),?\s*C[oó]digo\s*(?P<cod>[A-Z]{0,3}\s?\d{0,4}),?\s*Grado\s*(?P<gra>\d{1,2})", re.I)


def _limpio(txt: str | None) -> str:
    return re.sub(r"\s+", " ", txt or "").strip()


def separar_denominacion(txt: str) -> tuple[str, str | None, str | None]:
    m = _DCG.search(_limpio(txt))
    if not m:
        return _limpio(txt), None, None
    return m.group("den").strip(" ,"), m.group("cod").replace(" ", ""), m.group("gra")


def fecha_corte(texto: str) -> date | None:
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
    if m:
        d, mth, y = map(int, m.groups())
        try:
            return date(y, mth, d)
        except ValueError:
            return None
    return None


def vacantes_oficiales(ruta: Path) -> tuple[list[dict], date | None]:
    """Devuelve (cargos sin proveer, fecha de corte del informe)."""
    filas, texto = [], ""
    with pdfplumber.open(ruta) as pdf:
        for pg in pdf.pages:
            texto += (pg.extract_text() or "") + "\n"
            for tabla in pg.extract_tables():
                for fila in tabla:
                    celdas = [_limpio(c) for c in fila]
                    i = next((k for k, c in enumerate(celdas) if norm(c).startswith("vacancia")), None)
                    if i is None or "den" in norm(" ".join(celdas)) and "cod" in norm(" ".join(celdas)) and "vacancia" == norm(celdas[i]):
                        continue  # encabezado o fila sin vacancia
                    resto = celdas[i + 1:]
                    if not resto:
                        continue
                    den, cod, gra = separar_denominacion(resto[0])
                    filas.append({
                        "naturaleza": celdas[i - 1] if i > 0 else "",
                        "vacancia": celdas[i],
                        "denominacion": den, "codigo": cod, "grado": gra,
                        "dependencia": resto[1] if len(resto) > 1 else "",
                        "grupo": resto[2] if len(resto) > 2 else "",
                    })
    return filas, fecha_corte(texto)
