"""Genera el Excel consolidado (resumen + detalle) a partir de los resultados por entidad."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

HOJAS = {
    "vacantes_oficiales": "1. Vacantes oficiales",
    "balance": "1. Saldo por cargo",
    "retiros": "1. Retiros declarados",
    "contratos": "2. Contratos que terminan",
    "empleos": "Fichas del manual",
    "alertas": "Alertas",
}

NOTAS = [
    ("1. Vacantes oficiales", "Cargos sin proveer según el informe de planta publicado por la entidad, con el "
     "perfil (propósito y requisitos) de la ficha del manual de funciones."),
    ("1. Saldo por cargo", "Vacantes del informe + retiros declarados - ingresos declarados (Ley 2013) "
     "después del corte. Es una ESTIMACIÓN: confirme con la entidad."),
    ("1. Retiros declarados", "Servidores que publicaron declaración de RETIRO: el cargo pudo quedar libre."),
    ("2. Contratos que terminan", "Contratos de prestación de servicios (SECOP II) con fecha de fin en la "
     "ventana. No son cargos de planta: son necesidades que se liberan."),
]


def _df(resultados: list[dict], clave: str) -> pd.DataFrame:
    filas = []
    for r in resultados:
        for f in r.get(clave, []):
            if isinstance(f, str):
                f = {"valor": f}
            filas.append({"entidad_codigo": r["codigo"], "entidad": r["nombre"], **f})
    return pd.DataFrame(filas)


def excel(resultados: list[dict], destino: Path, desde: date | None = None, hasta: date | None = None) -> Path:
    resumen = pd.DataFrame([{
        "entidad_codigo": r["codigo"], "entidad": r["nombre"],
        "fichas_manual": len(r.get("empleos", [])),
        "corte_informe_planta": r.get("corte_planta", ""),
        "vacantes_informe_oficial": len(r.get("vacantes_oficiales", [])),
        "movimientos_desde": r.get("movimientos_desde", ""),
        "retiros_declarados": len(r.get("retiros", [])),
        "saldo_estimado_vacantes": sum(b["saldo_estimado"] for b in r.get("balance", [])),
        f"contratos_que_terminan {desde or ''}..{hasta or ''}": len(r.get("contratos", [])),
        "alertas": len(r.get("alertas", [])),
        "error": r.get("error", ""),
    } for r in resultados])
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        resumen.to_excel(xw, sheet_name="Resumen", index=False)
        pd.DataFrame(NOTAS, columns=["hoja", "cómo leerla"]).to_excel(
            xw, sheet_name="Resumen", index=False, startrow=len(resumen) + 3)
        for clave, hoja in HOJAS.items():
            df = _df(resultados, clave)
            (df if not df.empty else pd.DataFrame({"sin datos": []})).to_excel(xw, sheet_name=hoja, index=False)
        for hoja in xw.sheets.values():
            for col in hoja.columns:
                ancho = min(70, max(10, *(len(str(c.value or "")) for c in col[:200])))
                hoja.column_dimensions[col[0].column_letter].width = ancho
            hoja.freeze_panes = "A2"
    return destino


def guardar_json(resultado: dict, carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{resultado['codigo']}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, default=str), "utf8")
