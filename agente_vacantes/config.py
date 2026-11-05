"""Configuración central. Todo se puede sobrescribir con variables de entorno."""
import os
from pathlib import Path

SIGEP_BASE = os.getenv(
    "SIGEP_BASE", "https://www1.funcionpublica.gov.co/fdci/consultaCiudadana/index"
)
# Valores de tipoPersonaId. 25 viene del enlace del usuario. Si se dejan vacíos,
# el agente los detecta leyendo el <select> del formulario (por etiqueta).
SIGEP_TIPO_CONTRATISTA = os.getenv("SIGEP_TIPO_CONTRATISTA", "25")
SIGEP_TIPO_SERVIDOR = os.getenv("SIGEP_TIPO_SERVIDOR", "")
SIGEP_PAGE_SIZE = int(os.getenv("SIGEP_PAGE_SIZE", "100"))

# SECOP II - Contratos electrónicos (datos abiertos, API Socrata)
SECOP_URL = os.getenv("SECOP_URL", "https://www.datos.gov.co/resource/jbjy-vk9h.json")
SECOP_APP_TOKEN = os.getenv("SECOP_APP_TOKEN", "")  # opcional, sube el límite de peticiones

# Claude (opcional: si no hay credenciales se usan los extractores heurísticos)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
CLAUDE_FALLBACKS = os.getenv("CLAUDE_FALLBACKS", "1") == "1"

PAUSA_SEG = float(os.getenv("PAUSA_SEG", "1.0"))  # cortesía entre peticiones
CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache"))
INSUMOS_DIR = Path(os.getenv("INSUMOS_DIR", "insumos"))
USER_AGENT = os.getenv("USER_AGENT", "agente-vacantes/0.1 (consulta de datos publicos)")

# Navegador para el SIGEP: "chrome" (Google Chrome instalado, vía Playwright) o "http".
NAVEGADOR = os.getenv("NAVEGADOR", "chrome")
NAVEGADOR_VISIBLE = os.getenv("NAVEGADOR_VISIBLE", "1") == "1"  # ver Chrome mientras trabaja
NAVEGADOR_RUTA = os.getenv("NAVEGADOR_RUTA", "")  # ruta a chrome.exe si no se detecta solo
NAVEGADOR_TIMEOUT_MS = int(os.getenv("NAVEGADOR_TIMEOUT_MS", "60000"))
# Con Chrome: "formulario" (elige tipo y entidad y oprime Buscar, como una persona) o
# "url" (abre la URL de la consulta con los parámetros).
SIGEP_MODO = os.getenv("SIGEP_MODO", "formulario")
