"""Consulta de páginas con Google Chrome (Playwright).

Se usa para el SIGEP: el agente abre Chrome, entra a la página como lo haría una persona
y toma el HTML ya cargado. Usa el Chrome instalado en el PC (channel="chrome"), así que
no hace falta `playwright install`. Si Chrome no abre, se vuelve al cliente HTTP normal.
"""
from __future__ import annotations

import atexit
import logging
import time
from pathlib import Path
from urllib.parse import urlencode

from . import config

log = logging.getLogger(__name__)

_pw = None
_browser = None
_page = None
_falló = False


def disponible() -> bool:
    return config.NAVEGADOR == "chrome" and not _falló


def abierto() -> bool:
    return _page is not None


def _abrir():
    global _pw, _browser, _page, _falló
    if _page is not None:
        return _page
    try:
        from playwright.sync_api import sync_playwright
        _pw = sync_playwright().start()
        opciones = {"headless": not config.NAVEGADOR_VISIBLE}
        if config.NAVEGADOR_RUTA:
            opciones["executable_path"] = config.NAVEGADOR_RUTA
        else:
            opciones["channel"] = "chrome"
        _browser = _pw.chromium.launch(**opciones)
        _page = _browser.new_page(locale="es-CO")
        _page.set_default_timeout(config.NAVEGADOR_TIMEOUT_MS)
        atexit.register(cerrar)
        log.info("Google Chrome abierto para consultar el SIGEP")
        return _page
    except Exception as e:  # sin Playwright o sin Chrome instalado
        _falló = True
        log.warning("No se pudo abrir Google Chrome (%s). Se usa el cliente HTTP.", e)
        cerrar()
        return None


def ir(page, url: str, intentos: int = 3) -> None:
    """Navega con paciencia: el sitio puede tardar en responder. Reintenta y espera el formulario."""
    ultimo = None
    for i in range(1, intentos + 1):
        try:
            page.goto(url, wait_until="commit", timeout=config.NAVEGADOR_TIMEOUT_MS)
            page.wait_for_selector("form, table, select", timeout=config.NAVEGADOR_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            return
        except Exception as e:
            ultimo = e
            log.warning("La página no cargó (intento %d de %d): %s", i, intentos,
                        str(e).splitlines()[0])
            time.sleep(5 * i)
    raise ultimo


def cerrar() -> None:
    global _pw, _browser, _page
    for obj, metodo in ((_browser, "close"), (_pw, "stop")):
        try:
            if obj is not None:
                getattr(obj, metodo)()
        except Exception:
            pass
    _pw = _browser = _page = None


def url_con_params(url: str, params: dict | None) -> str:
    if not params:
        return url
    return url + ("&" if "?" in url else "?") + urlencode(params)


def obtener(url: str, params: dict | None = None) -> bytes | None:
    """Abre la URL en Chrome y devuelve el HTML ya cargado (None si Chrome no está)."""
    page = _abrir()
    if page is None:
        return None
    ir(page, url_con_params(url, params))
    time.sleep(config.PAUSA_SEG)
    return page.content().encode("utf8")


def estado_pagina() -> dict:
    """URL, título y comienzo del texto que muestra Chrome (para diagnosticar)."""
    if _page is None:
        return {}
    try:
        return {"url": _page.url, "titulo": _page.title(),
                "texto": (_page.inner_text("body") or "")[:500]}
    except Exception as e:
        return {"error": str(e).splitlines()[0]}


def captura(ruta: Path) -> bool:
    if _page is None:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _page.screenshot(path=str(ruta), full_page=True)
    return True


# ------------------------------------------------------------ uso del formulario SIGEP
# El campo "Nombre entidad" es una lista con buscador (select2 / autocompletar). Estas
# funciones la manejan como una persona: abrir, leer o escribir, elegir y oprimir Buscar.

_JS_OPCIONES = """() => {
  const s = document.querySelector('select[name=entidad], select#entidad');
  if (!s) return null;
  return Array.from(s.options).filter(o => o.value && o.value.trim())
              .map(o => [o.value.trim(), o.textContent.trim()]);
}"""


def _ir_al_formulario(page, url: str) -> None:
    ir(page, url)


def describir_campo_entidad(url: str) -> dict:
    """Cómo está construido el campo 'Nombre entidad' (para el informe de verificación)."""
    page = _abrir()
    if page is None:
        return {}
    _ir_al_formulario(page, url)
    return page.evaluate("""() => {
      const s = document.querySelector('select[name=entidad], select#entidad');
      const i = document.querySelector('input[name=entidad], input#entidad');
      return {
        select: !!s, opciones_en_select: s ? s.options.length : 0,
        input: !!i, select2: !!document.querySelector('.select2, .select2-container'),
        chosen: !!document.querySelector('.chosen-container'),
        fechas: Array.from(document.querySelectorAll('input')).filter(
            e => /fecha/i.test(e.name || e.id || '') || /dd\\/mm/i.test(e.placeholder || ''))
            .map(e => e.name || e.id),
        botones: Array.from(document.querySelectorAll('button, input[type=submit]'))
            .map(b => (b.innerText || b.value || '').trim()).filter(Boolean),
      };
    }""")


def listar_entidades(url: str) -> list[tuple[str, str]]:
    """Lee todas las opciones de 'Nombre entidad'. Devuelve [(valor, nombre)]."""
    page = _abrir()
    if page is None:
        return []
    _ir_al_formulario(page, url)
    opciones = page.evaluate(_JS_OPCIONES) or []
    if len(opciones) > 1:
        return [tuple(o) for o in opciones]
    # Lista que se llena al abrirla (select2 con carga por AJAX): abrir y desplazar,
    # capturando las respuestas JSON que trae la página ({results: [{id, text}]}).
    capturadas: dict[str, str] = {}

    def _al_responder(resp):
        try:
            if "json" not in (resp.headers.get("content-type") or ""):
                return
            datos = resp.json()
            lista = datos.get("results") if isinstance(datos, dict) else datos
            for it in lista or []:
                if isinstance(it, dict) and it.get("id") not in (None, "") and it.get("text"):
                    capturadas[str(it["id"])] = str(it["text"]).strip()
        except Exception:
            pass

    page.on("response", _al_responder)
    try:
        page.locator(".select2-selection, .select2-choice").first.click()
        page.wait_for_selector(".select2-results__option, .select2-result", timeout=15000)
        vistos = -1
        while True:
            items = page.locator(".select2-results__option, .select2-result")
            n = items.count()
            if n == vistos:
                break
            vistos = n
            items.nth(n - 1).scroll_into_view_if_needed()
            time.sleep(1.5)
        datos = page.evaluate("""() => Array.from(document.querySelectorAll(
            '.select2-results__option, .select2-result')).map(e => [
              (e.id || '').split('-').pop(), e.textContent.trim()])""")
        page.keyboard.press("Escape")
        if capturadas:
            return list(capturadas.items())
        opciones = page.evaluate(_JS_OPCIONES) or []
        if len(opciones) > 1:
            return [tuple(o) for o in opciones]
        # Sin código visible: se usa el nombre como código; la consulta elige por nombre.
        return [(d[0] or d[1], d[1]) for d in datos
                if d[1] and not d[1].lower().startswith(("(opcional", "buscando", "cargando", "no se encontr"))]
    except Exception as e:
        log.warning("No se pudo leer la lista 'Nombre entidad': %s", e)
        return []
    finally:
        page.remove_listener("response", _al_responder)


def _elegir_entidad(page, valor: str, nombre: str) -> bool:
    nombre = nombre or ("" if valor.isdigit() else valor)
    sel = page.locator("select[name=entidad], select#entidad").first
    if sel.count():
        try:
            tiene = page.evaluate(
                "v => !!Array.from(document.querySelector('select[name=entidad], select#entidad')"
                ".options).find(o => o.value === v)", valor)
            if tiene:
                sel.select_option(valor, force=True)
                page.evaluate("""() => { const s = document.querySelector('select[name=entidad], select#entidad');
                    s.dispatchEvent(new Event('change', {bubbles: true}));
                    if (window.jQuery) window.jQuery(s).trigger('change'); }""")
                return True
        except Exception:
            pass
    if not nombre:
        return False
    if page.locator(".select2-selection, .select2-choice").count():
        try:  # select2: abrir, escribir el nombre y elegir exactamente ese resultado
            page.locator(".select2-selection, .select2-choice").first.click()
            campo = page.locator(".select2-search__field, .select2-input").first
            opcion = page.locator(".select2-results__option, .select2-result").filter(
                has_text=nombre[:60]).first
            for intento in range(3):  # la lista puede seguir cargando: reintentar la búsqueda
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                campo.fill("")
                campo.type(nombre[:60], delay=20)
                try:
                    opcion.wait_for(state="visible", timeout=10000)
                    break
                except Exception:
                    if intento == 2:
                        raise
            opcion.click()
            elegido = page.locator(".select2-selection__rendered, .select2-chosen").first.inner_text()
            if _norm(elegido).lstrip("×").strip() == _norm(nombre):
                return True
            log.warning("Se eligió '%s' en lugar de '%s'", elegido, nombre)
            return False
        except Exception as e:
            log.warning("No se encontró '%s' en la lista de entidades: %s", nombre, e)
            return False
    try:  # autocompletar en un <input>
        campo = page.locator("input[name=entidad], input#entidad").first
        campo.fill(nombre[:60])
        page.wait_for_selector(".ui-menu-item, [role=option]", timeout=10000)
        page.locator(".ui-menu-item, [role=option]").filter(has_text=nombre[:40]).first.click()
        return True
    except Exception:
        return False


def _norm(t: str) -> str:
    from .sigep import norm
    return norm(t)


def _llenar_fechas(page, desde: str, hasta: str) -> None:
    for nombre, valor in (("fechaFinalizacionDesde", desde), ("fechaFinalizacionHasta", hasta)):
        campo = page.locator(f"input[name={nombre}], input#{nombre}").first
        if campo.count():
            campo.fill(valor)
            continue
    if not page.locator("input[name=fechaFinalizacionDesde], input#fechaFinalizacionDesde").count():
        campos = page.locator("input[placeholder*='dd/mm']")
        for i, valor in enumerate((desde, hasta)):
            if i < campos.count():
                campos.nth(i).fill(valor)
    page.keyboard.press("Escape")  # cerrar el calendario si se abrió


def _boton_siguiente(page):
    for sel in ("a.nextLink", "a[rel=next]", "li.next:not(.disabled) a",
                "a:text-is('Siguiente')", "a:text-is('»')", "a:text-is('>')"):
        loc = page.locator(sel).first
        if loc.count() and loc.is_visible():
            return loc
    return None


def buscar_en_formulario(url: str, tipo: str, entidad: str, nombre: str = "",
                         desde: str = "", hasta: str = "", max_paginas: int = 500) -> list[bytes] | None:
    """Llena el formulario como una persona y devuelve el HTML de cada página de resultados."""
    page = _abrir()
    if page is None:
        return None
    _ir_al_formulario(page, url)
    try:
        page.locator("select[name=tipoPersonaId], select#tipoPersonaId").first.select_option(tipo)
    except Exception as e:
        log.warning("No se pudo elegir el tipo de persona %s: %s", tipo, e)
    if not _elegir_entidad(page, entidad, nombre):
        log.warning("No se pudo elegir la entidad %s %s en el formulario", entidad, nombre)
        return []
    if desde or hasta:
        _llenar_fechas(page, desde, hasta)
    boton = page.locator("button:has-text('Buscar'), input[type=submit][value*='Buscar'], "
                         "[name=find]").first
    boton.click()
    paginas = []
    for _ in range(max_paginas):
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
        time.sleep(config.PAUSA_SEG)
        paginas.append(page.content().encode("utf8"))
        sig = _boton_siguiente(page)
        if sig is None:
            break
        sig.click()
    return paginas
