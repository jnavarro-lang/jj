"""Línea de comandos.

    python -m agente_vacantes entidades            # crea/actualiza entidades.csv desde Función Pública
    python -m agente_vacantes ejecutar [opciones]  # corre el cruce y genera el Excel
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from rapidfuzz import fuzz

from . import cruce, documentos, planta, reporte, secop, sigep
from .modelos import Empleo

log = logging.getLogger("agente_vacantes")
COLUMNAS_CSV = ["codigo", "nombre", "nit", "manual", "organigrama", "planta", "corte_planta"]


def leer_entidades(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf8") as f:
        return [{k: (v or "").strip() for k, v in fila.items()} for fila in csv.DictReader(f)]


def cmd_entidades(args) -> None:
    existentes = {e["codigo"]: e for e in leer_entidades(args.entidades)}
    for o in sigep.listar_entidades():
        existentes.setdefault(o.valor, {"codigo": o.valor, "nombre": o.etiqueta})
    with args.entidades.open("w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
        w.writeheader()
        for e in existentes.values():
            w.writerow({k: e.get(k, "") for k in COLUMNAS_CSV})
    print(f"{len(existentes)} entidades en {args.entidades}. Complete nit/manual/organigrama/planta "
          "(ruta local o URL; varios separados por |) o deje los archivos en insumos/<codigo>/.")


def _fmt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


class IndiceSecop:
    """Contratos de la ventana agrupados por entidad. Con pocas entidades consulta cada una
    (por NIT o nombre); con muchas, descarga una sola vez toda la ventana."""

    def __init__(self, desde: date, hasta: date, todos_los_tipos: bool, entidades: list[dict] | None = None):
        tipos = not todos_los_tipos
        if entidades is not None and len(entidades) <= 20:
            filas = []
            for e in entidades:
                if e.get("nit"):
                    filas += secop.contratos_por_vencer(desde, hasta, nit=e["nit"], solo_prestacion_servicios=tipos)
                elif e.get("nombre"):
                    filas += secop.contratos_por_vencer(desde, hasta, entidad=e["nombre"].rstrip(". "),
                                                        solo_prestacion_servicios=tipos)
        else:
            filas = secop.contratos_por_vencer(desde, hasta, solo_prestacion_servicios=tipos)
        self.por_nit, self.por_nombre = defaultdict(list), defaultdict(list)
        for f in filas:
            self.por_nit[secop.solo_digitos(f.get("nit_entidad"))[:9]].append(f)
            self.por_nombre[sigep.norm(f.get("entidad"))].append(f)
        log.info("SECOP II: %d contratos en la ventana", len(filas))

    def de(self, nombre: str, nit: str) -> list[dict]:
        clave = secop.solo_digitos(nit)[:9]
        if clave and clave in self.por_nit:
            return self.por_nit[clave]
        n = sigep.norm(nombre).rstrip(".")
        mejor = max(self.por_nombre, key=lambda k: fuzz.token_set_ratio(n, k), default=None)
        if mejor and fuzz.token_set_ratio(n, mejor) >= 95:
            return self.por_nombre[mejor]
        return []


class IndiceDeclaraciones:
    """Para muchas entidades: una sola consulta de todas las declaraciones, agrupadas por entidad."""

    def __init__(self, desde: date, hasta: date):
        self.por_entidad = defaultdict(list)
        for d in sigep.declaraciones("", _fmt(desde), _fmt(hasta)):
            self.por_entidad[sigep.norm(d.get("entidad"))].append(d)
        log.info("Declaraciones Ley 2013: %d", sum(map(len, self.por_entidad.values())))

    def de(self, nombre: str) -> list[dict]:
        return self.por_entidad.get(sigep.norm(nombre), [])


def _refs(valor: str | None) -> list[str | None]:
    partes = [p.strip() for p in (valor or "").split("|") if p.strip()]
    return partes or [None]


def _empleos(ent: dict, usar_ia: bool) -> tuple[list[Empleo], list[str]]:
    usados, empleos = [], []
    for ref in _refs(ent.get("manual")):
        for ruta in documentos.localizar_todos(ent["codigo"], "manual", ref):
            usados.append(str(ruta))
            if usar_ia:
                from . import extractor_ia
                nuevos = extractor_ia.extraer_empleos(ruta)
            else:
                nuevos = documentos.empleos_heuristico(documentos.texto(ruta))
            empleos.extend(nuevos)
    return empleos, usados


def procesar(ent: dict, args, usar_ia: bool, idx_secop: IndiceSecop | None,
             idx_decl: IndiceDeclaraciones | None) -> dict:
    r = {"codigo": ent["codigo"], "nombre": ent.get("nombre", "")}
    alertas = []

    empleos, r["manual"] = _empleos(ent, usar_ia)
    r["empleos"] = [e.model_dump() for e in empleos]

    oficiales, corte = [], None
    for ref in _refs(ent.get("planta")):
        for ruta in documentos.localizar_todos(ent["codigo"], "planta", ref):
            v, c = planta.vacantes_oficiales(ruta)
            oficiales += v
            corte = corte or c
    if ent.get("corte_planta"):
        corte = date.fromisoformat(ent["corte_planta"])
    r["corte_planta"] = corte.isoformat() if corte else ""

    deps: list[str] = []
    ruta_org = documentos.localizar(ent["codigo"], "organigrama", ent.get("organigrama"))
    if ruta_org:
        r["organigrama"] = str(ruta_org)
        if usar_ia:
            from . import extractor_ia
            deps = extractor_ia.extraer_dependencias(ruta_org)
        else:
            deps = documentos.dependencias_heuristico(documentos.texto(ruta_org))
    deps = deps or sorted({v["dependencia"] for v in oficiales if v.get("dependencia")} |
                          {e.area_funcional.split(" - ")[0] for e in empleos if e.area_funcional})
    r["dependencias"] = deps

    # Movimientos de planta: desde el corte del informe oficial (o desde --desde) hasta hoy
    mov_desde = args.movimientos_desde or (corte if corte else args.desde)
    decl = []
    if not args.sin_sigep:
        if idx_decl:
            decl = [d for d in idx_decl.de(r["nombre"]) if d.get("fecha", "")[:10] >= mov_desde.isoformat()]
        else:
            decl = sigep.declaraciones(ent["codigo"], _fmt(mov_desde), _fmt(date.today()))
    r["movimientos_desde"] = mov_desde.isoformat()
    r["n_declaraciones"] = len(decl)

    detalle, balance, retiros = cruce.vacantes_planta(oficiales, decl, empleos)
    r["vacantes_oficiales"], r["balance"], r["retiros"] = detalle, balance, retiros

    contratos = idx_secop.de(r["nombre"], ent.get("nit", "")) if idx_secop else []
    r["contratos"] = cruce.contratos_que_se_liberan(contratos, deps, empleos, cruce.siglas_de(oficiales))

    if not empleos:
        alertas.append({"tipo": "Sin manual de funciones", "detalle": "No hay perfiles: agregue el manual."})
    if not oficiales:
        alertas.append({"tipo": "Sin informe oficial de vacantes",
                        "detalle": "El saldo se calcula solo con retiros/ingresos declarados; es una señal, no un conteo."})
    elif corte and (date.today() - corte).days > 180:
        alertas.append({"tipo": "Informe de planta desactualizado",
                        "detalle": f"Corte {corte.isoformat()}: verifique si hay un informe más reciente."})
    if not decl and not args.sin_sigep:
        alertas.append({"tipo": "Sin declaraciones Ley 2013", "detalle": "No se encontraron movimientos en el periodo."})
    if idx_secop and not contratos:
        alertas.append({"tipo": "Sin contratos en SECOP II", "detalle": "Revise el NIT de la entidad en entidades.csv."})
    r["alertas"] = alertas
    return r


def cmd_ejecutar(args) -> None:
    entidades = leer_entidades(args.entidades)
    if args.codigo:
        entidades = [e for e in entidades if e["codigo"] in args.codigo] or \
                    [{"codigo": c, "nombre": ""} for c in args.codigo]
    if not entidades:
        sys.exit("No hay entidades. Ejecute primero: python -m agente_vacantes entidades")
    if any(not e.get("nombre") for e in entidades) and not args.sin_sigep:
        nombres = {o.valor: o.etiqueta for o in sigep.listar_entidades()}
        for e in entidades:
            e["nombre"] = e.get("nombre") or nombres.get(e["codigo"], "")

    usar_ia = not args.sin_ia
    if usar_ia:
        from . import extractor_ia
        if not extractor_ia.disponible():
            log.warning("Sin credenciales de Anthropic: se usa el extractor heurístico.")
            usar_ia = False

    idx_secop = None if args.sin_secop else IndiceSecop(args.desde, args.hasta, args.todos_los_tipos, entidades)
    idx_decl = None
    if not args.sin_sigep and len(entidades) > 20:  # una sola consulta para todas
        idx_decl = IndiceDeclaraciones(args.movimientos_desde or args.desde, date.today())

    carpeta = args.salida / "entidades"
    resultados = []
    for n, ent in enumerate(entidades, 1):
        previo = carpeta / f"{ent['codigo']}.json"
        if previo.exists() and not args.rehacer:
            resultados.append(json.loads(previo.read_text("utf8")))
            continue
        log.info("[%d/%d] %s %s", n, len(entidades), ent["codigo"], ent.get("nombre", ""))
        try:
            r = procesar(ent, args, usar_ia, idx_secop, idx_decl)
        except Exception as e:  # una entidad con problemas no detiene el recorrido
            log.exception("Error en %s", ent["codigo"])
            r = {"codigo": ent["codigo"], "nombre": ent.get("nombre", ""), "error": str(e)}
        reporte.guardar_json(r, carpeta)
        resultados.append(r)

    destino = reporte.excel(resultados, args.salida / f"vacantes_{datetime.now():%Y%m%d_%H%M}.xlsx",
                            args.desde, args.hasta)
    print(f"Listo: {destino}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="agente_vacantes")
    p.add_argument("--entidades", type=Path, default=Path("entidades.csv"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("entidades", help="Lista las entidades de Función Pública en entidades.csv")
    e = sub.add_parser("ejecutar", help="Cruza y genera el Excel")
    e.add_argument("--codigo", nargs="*", help="Códigos de entidad a procesar (por defecto todas)")
    e.add_argument("--desde", type=date.fromisoformat, default=date(2026, 8, 1),
                   help="Inicio de la ventana de fin de contratos (SECOP II)")
    e.add_argument("--hasta", type=date.fromisoformat, default=date(2026, 11, 30))
    e.add_argument("--movimientos-desde", type=date.fromisoformat, default=None,
                   help="Inicio de retiros/ingresos declarados (por defecto, el corte del informe de planta)")
    e.add_argument("--salida", type=Path, default=Path("salida"))
    e.add_argument("--sin-ia", action="store_true", help="No usar Claude para leer documentos")
    e.add_argument("--sin-sigep", action="store_true", help="No consultar declaraciones Ley 2013")
    e.add_argument("--sin-secop", action="store_true")
    e.add_argument("--todos-los-tipos", action="store_true",
                   help="SECOP: incluir todos los tipos de contrato, no solo prestación de servicios")
    e.add_argument("--rehacer", action="store_true", help="Ignorar resultados ya guardados")
    args = p.parse_args(argv)
    {"entidades": cmd_entidades, "ejecutar": cmd_ejecutar}[args.cmd](args)


if __name__ == "__main__":
    main()
