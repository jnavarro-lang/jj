"""SECOP II - Contratos electrónicos (datos.gov.co, API Socrata).

Sirve para la opción 2 en todas las entidades: contratos que terminan en una ventana de
fechas, con objeto, valor, contratista y enlace al proceso.
"""
from __future__ import annotations

import json
from datetime import date

from . import config, http

CAMPOS = {
    "entidad": "nombre_entidad",
    "nit_entidad": "nit_entidad",
    "id_contrato": "id_contrato",
    "referencia": "referencia_del_contrato",
    "objeto": "objeto_del_contrato",
    "descripcion": "descripcion_del_proceso",
    "tipo_contrato": "tipo_de_contrato",
    "modalidad": "modalidad_de_contratacion",
    "estado": "estado_contrato",
    "fecha_inicio": "fecha_de_inicio_del_contrato",
    "fecha_fin": "fecha_de_fin_del_contrato",
    "valor": "valor_del_contrato",
    "contratista": "proveedor_adjudicado",
    "documento_contratista": "documento_proveedor",
    "departamento": "departamento",
    "ciudad": "ciudad",
    "url": "urlproceso",
}


def _q(valor: str) -> str:
    return valor.replace("'", "''")


def contratos_por_vencer(desde: date, hasta: date, nit: str | None = None,
                         entidad: str | None = None, solo_prestacion_servicios: bool = True,
                         lote: int = 50000) -> list[dict]:
    where = [
        f"{CAMPOS['fecha_fin']} between '{desde.isoformat()}T00:00:00' "
        f"and '{hasta.isoformat()}T23:59:59'"
    ]
    if nit:
        where.append(f"{CAMPOS['nit_entidad']} = '{_q(nit)}'")
    if entidad:
        where.append(f"upper({CAMPOS['entidad']}) like upper('%{_q(entidad)}%')")
    if solo_prestacion_servicios:
        where.append(f"upper({CAMPOS['tipo_contrato']}) like '%PRESTACI%'")
    headers = {"X-App-Token": config.SECOP_APP_TOKEN} if config.SECOP_APP_TOKEN else None

    salida, offset = [], 0
    while True:
        params = {"$where": " and ".join(where), "$limit": lote, "$offset": offset,
                  "$order": f"{CAMPOS['nit_entidad']}, {CAMPOS['fecha_fin']}"}
        filas = json.loads(http.get(config.SECOP_URL, params=params, headers=headers))
        salida.extend(normalizar(f) for f in filas)
        if len(filas) < lote:
            return salida
        offset += lote


def normalizar(fila: dict) -> dict:
    reg = {k: fila.get(v) for k, v in CAMPOS.items()}
    if isinstance(reg["url"], dict):
        reg["url"] = reg["url"].get("url")
    for f in ("fecha_inicio", "fecha_fin"):
        if reg[f]:
            reg[f] = str(reg[f])[:10]
    reg["fuente"] = "SECOP II"
    return reg
