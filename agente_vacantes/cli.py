"""Línea de comandos.

    python -m agente_vacantes entidades            # crea/actualiza entidades.csv desde SIGEP
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

from . import cruce, documentos, reporte, secop, sigep
from .modelos import Empleo

log = logging.getLogger("agente_vacantes")
COLUMNAS_CSV = ["codigo", "nombre", "nit", "manual", "organigrama", "planta"]


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
          "(ruta local o URL) o deje los archivos en insumos/<codigo>/.")


class IndiceSecop:
    """Descarga una sola vez los contratos de la ventana y los agrupa por entidad."""

    def __init__(self, desde: date, hasta: date, todos_los_tipos: bool):
        filas = secop.contratos_por_vencer(desde, hasta, solo_prestacion_servicios=not todos_los_tipos)
        self.por_nit, self.por_nombre = defaultdict(list), defaultdict(list)
        for f in filas:
            self.por_nit[(f.get("nit_entidad") or "").split("-")[0].strip()].append(f)
            self.por_nombre[sigep.norm(f.get("entidad"))].append(f)
        log.info("SECOP II: %d contratos en la ventana", len(filas))

    def de(self, nombre: str, nit: str) -> list[dict]:
        if nit and nit.split("-")[0].strip() in self.por_nit:
            return self.por_nit[nit.split("-")[0].strip()]
        n = sigep.norm(nombre)
        if n in self.por_nombre:
            return self.por_nombre[n]
        mejor = max(self.por_nombre, key=lambda k: fuzz.token_sort_ratio(n, k), default=None)
        if mejor and fuzz.token_sort_ratio(n, mejor) >= 92:
            return self.por_nombre[mejor]
        return []


def _empleos(ent: dict, usar_ia: bool) -> tuple[list[Empleo], str]:
    usados = []
    empleos: list[Empleo] = []
    for tipo in ("planta", "manual"):  # el decreto de planta suele traer el número de cargos
        ruta = documentos.localizar(ent["codigo"], tipo, ent.get(tipo))
        if not ruta:
            continue
        usados.append(str(ruta))
        if usar_ia:
            from . import extractor_ia
            nuevos = extractor_ia.extraer_empleos(ruta)
        else:
            nuevos = documentos.empleos_heuristico(documentos.texto(ruta))
        empleos = _fusionar(empleos, nuevos)
    return empleos, "; ".join(usados)


def _fusionar(base: list[Empleo], nuevos: list[Empleo]) -> list[Empleo]:
    idx = {(sigep.norm(e.denominacion), e.codigo, e.grado): e for e in base}
    for e in nuevos:
        k = (sigep.norm(e.denominacion), e.codigo, e.grado)
        if k in idx:
            for campo, valor in e.model_dump().items():
                if valor and not getattr(idx[k], campo):
                    setattr(idx[k], campo, valor)
        else:
            idx[k] = e
            base.append(e)
    return base


def procesar(ent: dict, args, tipos: dict, indice: IndiceSecop | None, usar_ia: bool) -> dict:
    r = {"codigo": ent["codigo"], "nombre": ent.get("nombre", "")}
    fmt = lambda d: d.strftime("%d/%m/%Y")
    empleos, r["manual"] = _empleos(ent, usar_ia)
    r["empleos"] = [e.model_dump() for e in empleos]

    ruta_org = documentos.localizar(ent["codigo"], "organigrama", ent.get("organigrama"))
    deps: list[str] = []
    if ruta_org:
        r["organigrama"] = str(ruta_org)
        if usar_ia:
            from . import extractor_ia
            deps = extractor_ia.extraer_dependencias(ruta_org)
        else:
            deps = documentos.dependencias_heuristico(documentos.texto(ruta_org))
    deps = deps or sorted({e.dependencia for e in empleos if e.dependencia
                           and not any(g in sigep.norm(e.dependencia) for g in cruce.DEP_GENERICA)})
    r["dependencias"] = deps

    servidores, contratos = [], []
    if not args.sin_sigep:
        if tipos.get("servidor"):
            servidores = sigep.consultar(ent["codigo"], tipos["servidor"])
        contratos = [dict(c, fuente="SIGEP") for c in
                     sigep.consultar(ent["codigo"], tipos["contratista"], fmt(args.desde), fmt(args.hasta))]
    if indice:
        contratos += indice.de(r["nombre"], ent.get("nit", ""))
    r["n_servidores"] = len(servidores)
    r["ocupacion_verificada"] = bool(servidores)

    alertas = []
    if not empleos:
        alertas.append({"tipo": "Sin manual de funciones", "detalle":
                        "No se encontró manual/planta: no se pueden calcular vacantes de planta."})
    if not tipos.get("servidor") and not args.sin_sigep:
        alertas.append({"tipo": "Sin consulta de servidores", "detalle":
                        "No se detectó el tipoPersonaId de servidores públicos; defina SIGEP_TIPO_SERVIDOR."})
    if empleos and not servidores:
        alertas.append({"tipo": "Ocupación no verificada", "detalle":
                        "No hay servidores del SIGEP para esta entidad: las 'vacantes' equivalen al total "
                        "de plazas y NO deben tomarse como vacantes reales."})
    vac, al = cruce.vacantes_planta(empleos, servidores) if empleos else ([], [])
    r["vacantes_planta"], r["alertas"] = vac, alertas + al
    r["contratos"] = cruce.contratos_que_se_liberan(contratos, deps, empleos)
    return r


def cmd_ejecutar(args) -> None:
    entidades = leer_entidades(args.entidades)
    if args.codigo:
        entidades = [e for e in entidades if e["codigo"] in args.codigo] or \
                    [{"codigo": c, "nombre": ""} for c in args.codigo]
    if not entidades:
        sys.exit("No hay entidades. Ejecute primero: python -m agente_vacantes entidades")

    usar_ia = not args.sin_ia
    if usar_ia:
        from . import extractor_ia
        if not extractor_ia.disponible():
            log.warning("Sin credenciales de Anthropic: se usa el extractor heurístico.")
            usar_ia = False

    tipos = {} if args.sin_sigep else sigep.tipos_persona()
    indice = None if args.sin_secop else IndiceSecop(args.desde, args.hasta, args.todos_los_tipos)

    carpeta = args.salida / "entidades"
    resultados = []
    for n, ent in enumerate(entidades, 1):
        previo = carpeta / f"{ent['codigo']}.json"
        if previo.exists() and not args.rehacer:
            resultados.append(json.loads(previo.read_text("utf8")))
            continue
        log.info("[%d/%d] %s %s", n, len(entidades), ent["codigo"], ent.get("nombre", ""))
        try:
            r = procesar(ent, args, tipos, indice, usar_ia)
        except Exception as e:  # una entidad con problemas no detiene el recorrido
            log.exception("Error en %s", ent["codigo"])
            r = {"codigo": ent["codigo"], "nombre": ent.get("nombre", ""), "error": str(e)}
        reporte.guardar_json(r, carpeta)
        resultados.append(r)

    destino = reporte.excel(resultados, args.salida / f"vacantes_{datetime.now():%Y%m%d_%H%M}.xlsx")
    print(f"Listo: {destino}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="agente_vacantes")
    p.add_argument("--entidades", type=Path, default=Path("entidades.csv"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("entidades", help="Lista las entidades del SIGEP en entidades.csv")
    e = sub.add_parser("ejecutar", help="Cruza y genera el Excel")
    e.add_argument("--codigo", nargs="*", help="Códigos SIGEP a procesar (por defecto todas)")
    e.add_argument("--desde", type=date.fromisoformat, default=date(2026, 8, 1))
    e.add_argument("--hasta", type=date.fromisoformat, default=date(2026, 11, 30))
    e.add_argument("--salida", type=Path, default=Path("salida"))
    e.add_argument("--sin-ia", action="store_true", help="No usar Claude para leer documentos")
    e.add_argument("--sin-sigep", action="store_true")
    e.add_argument("--sin-secop", action="store_true")
    e.add_argument("--todos-los-tipos", action="store_true",
                   help="SECOP: incluir todos los tipos de contrato, no solo prestación de servicios")
    e.add_argument("--rehacer", action="store_true", help="Ignorar resultados ya guardados")
    args = p.parse_args(argv)
    {"entidades": cmd_entidades, "ejecutar": cmd_ejecutar}[args.cmd](args)


if __name__ == "__main__":
    main()
