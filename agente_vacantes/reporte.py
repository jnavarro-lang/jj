"""Genera el Excel consolidado (resumen + detalle) a partir de los resultados por entidad."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

HOJAS = {
    "vacantes_planta": "Vacantes planta",
    "contratos": "Contratos que se liberan",
    "dependencias": "Dependencias",
    "alertas": "Alertas",
}


def _df(resultados: list[dict], clave: str) -> pd.DataFrame:
    filas = []
    for r in resultados:
        for f in r.get(clave, []):
            if isinstance(f, str):
                f = {"dependencia": f}
            filas.append({"entidad_codigo": r["codigo"], "entidad": r["nombre"], **f})
    return pd.DataFrame(filas)


def excel(resultados: list[dict], destino: Path) -> Path:
    resumen = pd.DataFrame([{
        "entidad_codigo": r["codigo"], "entidad": r["nombre"],
        "manual_encontrado": r.get("manual") or "NO",
        "organigrama_encontrado": r.get("organigrama") or "NO",
        "empleos_en_manual": len(r.get("empleos", [])),
        "plazas": sum(f["plazas"] for f in r.get("vacantes_planta", [])),
        "servidores_sigep": r.get("n_servidores", 0),
        "ocupacion_verificada": "SI" if r.get("ocupacion_verificada") else "NO",
        "vacantes_probables": sum(f["vacantes"] for f in r.get("vacantes_planta", []))
        if r.get("ocupacion_verificada") else "",
        "contratos_que_se_liberan": len(r.get("contratos", [])),
        "error": r.get("error", ""),
    } for r in resultados])
    destino.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(destino, engine="openpyxl") as xw:
        resumen.to_excel(xw, sheet_name="Resumen", index=False)
        vac = _df(resultados, "vacantes_planta")
        if not vac.empty:
            vac = vac[vac["vacantes"] > 0]
        for clave, hoja in HOJAS.items():
            df = vac if clave == "vacantes_planta" else _df(resultados, clave)
            (df if not df.empty else pd.DataFrame({"sin datos": []})).to_excel(xw, sheet_name=hoja, index=False)
        for hoja in xw.sheets.values():
            for col in hoja.columns:
                ancho = min(60, max(10, *(len(str(c.value or "")) for c in col[:200])))
                hoja.column_dimensions[col[0].column_letter].width = ancho
            hoja.freeze_panes = "A2"
    return destino


def guardar_json(resultado: dict, carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / f"{resultado['codigo']}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1, default=str), "utf8")
