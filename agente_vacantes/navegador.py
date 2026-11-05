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
    page.goto(url_con_params(url, params), wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass  # algunas páginas nunca quedan "quietas"; el DOM ya está
    time.sleep(config.PAUSA_SEG)
    return page.content().encode("utf8")


def captura(ruta: Path) -> bool:
    if _page is None:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _page.screenshot(path=str(ruta), full_page=True)
    return True
