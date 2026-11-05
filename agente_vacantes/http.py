"""Cliente HTTP con reintentos, pausa de cortesía y caché en disco."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config

_session: requests.Session | None = None
_ultima = 0.0


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504))
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = config.USER_AGENT
        _session = s
    return _session


def _cache_path(url: str, params: dict | None) -> Path:
    clave = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    return config.CACHE_DIR / "http" / hashlib.sha256(clave.encode()).hexdigest()


def get(url: str, params: dict | None = None, headers: dict | None = None,
        usar_cache: bool = True, timeout: int = 60) -> bytes:
    """GET que devuelve el cuerpo en bytes. Respeta config.PAUSA_SEG entre peticiones."""
    global _ultima
    ruta = _cache_path(url, params)
    if usar_cache and ruta.exists():
        return ruta.read_bytes()
    espera = config.PAUSA_SEG - (time.time() - _ultima)
    if espera > 0:
        time.sleep(espera)
    r = session().get(url, params=params, headers=headers, timeout=timeout)
    _ultima = time.time()
    r.raise_for_status()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(r.content)
    return r.content
