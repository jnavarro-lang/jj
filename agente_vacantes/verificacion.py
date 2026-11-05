"""Comando `verificar`: abre el SIGEP en Google Chrome y revisa su estructura real.

Deja en la carpeta `verificacion/` el HTML de la página, capturas de pantalla y un
informe.txt con lo que el agente reconoce (y lo que no), para ajustar el parser.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from . import config, http, navegador, secop, sigep


def _params(entidad: str, tipo: str, desde: date, hasta: date) -> dict:
    return {
        "tipoPersonaId": tipo, "primerNombre": "", "segundoNombre": "", "primerApellido": "",
        "segundoApellido": "", "numeroDocumento": "", "entidad": entidad,
        "fechaFinalizacionDesde": desde.strftime("%d/%m/%Y"),
        "fechaFinalizacionHasta": hasta.strftime("%d/%m/%Y"), "find": "Find",
    }


def _tablas(html: bytes) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    salida = []
    for i, t in enumerate(soup.find_all("table")):
        filas = t.find_all("tr")
        cab = [c.get_text(" ", strip=True) for c in (filas[0].find_all(["th", "td"]) if filas else [])]
        salida.append({"tabla": i, "filas": len(filas), "encabezados": cab,
                       "campos_reconocidos": {h: sigep._campo_para(h) for h in cab}})
    return salida


def _enlaces_paginacion(html: bytes) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    claves = ("offset", "max", "page", "pagina")
    return sorted({a["href"] for a in soup.find_all("a", href=True)
                   if any(k + "=" in a["href"].lower() for k in claves)})[:20]


def ejecutar(codigo: str, desde: date, hasta: date, carpeta: Path = Path("verificacion")) -> Path:
    carpeta.mkdir(parents=True, exist_ok=True)
    lineas: list[str] = []
    p = lineas.append
    p(f"Verificación SIGEP - entidad {codigo} - ventana {desde:%d/%m/%Y} a {hasta:%d/%m/%Y}")
    p(f"Página: {config.SIGEP_BASE}")

    # 1. Formulario
    try:
        form = http.get(config.SIGEP_BASE, usar_cache=False, navegador=True)
    except Exception as e:
        p(f"\n[ERROR] Chrome no pudo abrir la página: {str(e).splitlines()[0]}")
        try:
            navegador.captura(carpeta / "error_chrome.png")
        except Exception:
            pass
        p(f"Lo que muestra Chrome: {json.dumps(navegador.estado_pagina(), ensure_ascii=False)}")
        p("\nDiagnóstico sin Chrome (cliente HTTP):")
        p(_diagnostico_http())
        return _guardar(carpeta, lineas)
    (carpeta / "formulario.html").write_bytes(form)
    p(f"Modo: {'Google Chrome' if navegador.abierto() else 'cliente HTTP (Chrome no se pudo abrir)'}")
    navegador.captura(carpeta / "formulario.png")
    titulo = BeautifulSoup(form, "lxml").title
    p(f"\nTítulo de la página: {titulo.get_text(strip=True) if titulo else '(sin título)'}")

    tipos = sigep.opciones_select(form, "tipoPersonaId")
    p(f"\nOpciones de 'Tipo de persona' (tipoPersonaId): {len(tipos)}")
    for o in tipos:
        p(f"  {o.valor} = {o.etiqueta}")
    campo = navegador.describir_campo_entidad(config.SIGEP_BASE) if navegador.abierto() else {}
    if campo:
        p(f"\nCampo 'Nombre entidad': {json.dumps(campo, ensure_ascii=False)}")
    entidades = sigep.listar_entidades()
    p(f"\nEntidades en el formulario: {len(entidades)}")
    nombre = next((o.etiqueta for o in entidades if o.valor == codigo), None)
    p(f"Entidad {codigo}: {nombre or '(no aparece en la lista del formulario)'}")
    if not entidades:
        sel = [s.get('name') or s.get('id') for s in BeautifulSoup(form, 'lxml').find_all(['select', 'input'])]
        p(f"  Campos del formulario encontrados: {sel}")

    # 2. Consulta por cada tipo de persona
    lista_tipos = [(o.valor, o.etiqueta) for o in tipos] or [("25", "NATURAL"), ("26", "JURÍDICA")]
    for valor, etiqueta in lista_tipos:
        p(f"\n=== Consulta tipoPersonaId={valor} ({etiqueta}) ===")
        try:
            paginas = None
            if navegador.abierto() and config.SIGEP_MODO == "formulario":
                paginas = navegador.buscar_en_formulario(
                    config.SIGEP_BASE, valor, codigo, nombre or "",
                    desde.strftime("%d/%m/%Y"), hasta.strftime("%d/%m/%Y"), max_paginas=3)
                p(f"Modo formulario (elegir entidad + Buscar): {len(paginas or [])} página(s) leídas")
            if paginas:
                html = paginas[0]
                for i, extra in enumerate(paginas[1:], 2):
                    (carpeta / f"resultados_tipo{valor}_pag{i}.html").write_bytes(extra)
                filas_todas = sigep._filas_de_paginas(paginas, codigo, valor)
                p(f"Filas en las páginas leídas: {len(filas_todas)}")
            else:
                html = http.get(config.SIGEP_BASE, params=_params(codigo, valor, desde, hasta),
                                usar_cache=False, navegador=True)
                p("Modo URL (consulta con parámetros)")
        except Exception as e:
            p(f"[ERROR] {e}")
            continue
        (carpeta / f"resultados_tipo{valor}.html").write_bytes(html)
        navegador.captura(carpeta / f"resultados_tipo{valor}.png")
        p(f"Total que indica la página: {sigep.total_resultados(html)}")
        for t in _tablas(html):
            p(f"Tabla {t['tabla']}: {t['filas']} filas")
            for h, c in t["campos_reconocidos"].items():
                p(f"   columna '{h}' -> {c or 'NO RECONOCIDA'}")
        filas = sigep.parsear_resultados(html)
        p(f"Filas que el agente extrae de la primera página: {len(filas)}")
        for f in filas[:5]:
            p("   " + json.dumps(f, ensure_ascii=False))
        p(f"Enlace 'siguiente' detectado: {sigep.siguiente_pagina(html)}")
        enl = _enlaces_paginacion(html)
        p(f"Enlaces de paginación ({len(enl)}): " + (", ".join(enl) if enl else "ninguno"))

    # 3. SECOP II (nombres de campos)
    p("\n=== SECOP II (datos.gov.co) ===")
    try:
        filas = json.loads(http.get(config.SECOP_URL, params={"$limit": 50}, usar_cache=False))
        reales = set().union(*filas) if filas else set()  # Socrata omite campos vacíos
        p(f"Campos recibidos: {sorted(reales)}")
        faltan = {k: v for k, v in secop.CAMPOS.items() if v not in reales}
        p("Campos que el agente espera y no llegaron: " + (json.dumps(faltan) if faltan else "ninguno"))
    except Exception as e:
        p(f"[ERROR] No se pudo consultar SECOP II: {e}")

    return _guardar(carpeta, lineas)


def _diagnostico_http() -> str:
    import time
    import requests
    ini = time.time()
    try:
        r = requests.get(config.SIGEP_BASE, timeout=120, headers={"User-Agent": config.USER_AGENT})
        return (f"  HTTP {r.status_code} en {time.time() - ini:.1f} s, {len(r.content)} bytes, "
                f"servidor={r.headers.get('server')}, contiene formulario={'<form' in r.text.lower()}")
    except Exception as e:
        return f"  falló en {time.time() - ini:.1f} s: {e}"


def _guardar(carpeta: Path, lineas: list[str]) -> Path:
    destino = carpeta / "informe.txt"
    destino.write_text("\n".join(lineas) + "\n", "utf8")
    print("\n".join(lineas))
    print(f"\nInforme y archivos en: {carpeta.resolve()}")
    return destino
