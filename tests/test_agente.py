"""Pruebas con datos SINTÉTICOS (no son datos reales de ninguna entidad)."""
from agente_vacantes import cruce, documentos, sigep
from agente_vacantes.modelos import Empleo

HTML = """
<form><select name="tipoPersonaId"><option value="">--</option>
<option value="24">Servidor Público</option><option value="25">Contratista</option></select>
<select name="entidad"><option value="5202">ENTIDAD DE PRUEBA</option></select></form>
<p>Se encontraron 3 resultados</p>
<table><tr><th>Nombre</th><th>Cargo</th><th>Dependencia</th><th>Fecha Finalización</th></tr>
<tr><td><a href="/fdci/hv/1">ANA PEREZ</a></td><td>PROFESIONAL UNIVERSITARIO 219-01</td><td>Secretaría de Hacienda</td><td>30/09/2026</td></tr>
<tr><td>LUIS GOMEZ</td><td>PROFESIONAL UNIVERSITARIO 219-01</td><td>Secretaría de Salud</td><td>15/10/2026</td></tr>
<tr><td>EVA RUIZ</td><td>TECNICO OPERATIVO 314-02</td><td>Secretaría de Salud</td><td>01/11/2026</td></tr>
</table><a class="nextLink" href="/fdci/consultaCiudadana/index?offset=100&max=100">Siguiente</a>
"""

MANUAL = """
I. IDENTIFICACIÓN DEL EMPLEO
Nivel: Profesional
Denominación del empleo: Profesional Universitario
Código: 219
Grado: 01
No. de cargos: 3
Dependencia: Donde se ubique el cargo
III. PROPÓSITO PRINCIPAL
Gestionar los procesos financieros y presupuestales de la entidad.
VII. REQUISITOS DE FORMACIÓN ACADÉMICA Y EXPERIENCIA
Título profesional en Contaduría Pública o Economía. Experiencia: doce meses de experiencia profesional relacionada.
I. IDENTIFICACIÓN DEL EMPLEO
Nivel: Técnico
Denominación del empleo: Técnico Operativo
Código: 314
Grado: 02
No. de cargos: 1
Dependencia: Secretaría de Salud
"""


def test_parser_sigep():
    assert [o.valor for o in sigep.opciones_select(HTML, "tipoPersonaId")] == ["24", "25"]
    filas = sigep.parsear_resultados(HTML)
    assert len(filas) == 3
    assert filas[0]["nombre"] == "ANA PEREZ" and filas[0]["fecha_fin"] == "30/09/2026"
    assert filas[0]["detalle_url"].endswith("/fdci/hv/1")
    assert "offset=100" in sigep.siguiente_pagina(HTML)
    assert sigep.total_resultados(HTML) == 3


def test_manual_heuristico():
    empleos = documentos.empleos_heuristico(MANUAL)
    assert [(e.denominacion, e.codigo, e.grado, e.numero_cargos) for e in empleos] == [
        ("Profesional Universitario", "219", "01", 3), ("Técnico Operativo", "314", "02", 1)]
    assert "Contaduría" in empleos[0].requisitos_estudio


def test_vacantes_planta():
    empleos = documentos.empleos_heuristico(MANUAL)
    servidores = sigep.parsear_resultados(HTML)
    filas, alertas = cruce.vacantes_planta(empleos, servidores)
    assert [(f["plazas"], f["ocupadas"], f["vacantes"]) for f in filas] == [(3, 2, 1), (1, 1, 0)]
    assert alertas == []


def test_codigo_grado_distinto_no_ocupa():
    e = Empleo(denominacion="Profesional Universitario", codigo="219", grado="02", numero_cargos=1)
    filas, alertas = cruce.vacantes_planta([e], [{"nombre": "X", "cargo": "PROFESIONAL UNIVERSITARIO 219-01"}])
    assert filas[0]["vacantes"] == 1 and len(alertas) == 1


def test_contratos_que_se_liberan():
    deps = ["Secretaría de Hacienda", "Secretaría de Salud"]
    contratos = [
        {"fuente": "SECOP II", "contratista": "PEDRO", "fecha_fin": "2026-10-31",
         "objeto": "Prestación de servicios profesionales como abogado para la Secretaría de Salud"},
        {"fuente": "SIGEP", "nombre": "PEDRO", "fecha_fin": "2026-10-31", "objeto": "duplicado"},
    ]
    filas = cruce.contratos_que_se_liberan(contratos, deps, [])
    assert len(filas) == 1
    assert filas[0]["dependencia"] == "Secretaría de Salud"
    assert filas[0]["nivel_inferido"] == "Profesional" and "abogad" in filas[0]["formacion_mencionada"]


def test_indice_secop_por_entidad_no_descarga_todo(monkeypatch):
    from datetime import date
    from agente_vacantes import cli, secop
    llamadas = []

    def falso(desde, hasta, nit=None, entidad=None, solo_prestacion_servicios=True, lote=50000):
        llamadas.append((nit, entidad))
        return [{"nit_entidad": nit, "entidad": entidad}]

    monkeypatch.setattr(secop, "contratos_por_vencer", falso)
    ind = cli.IndiceSecop(date(2026, 8, 1), date(2026, 11, 30), False, precargar=False)
    assert llamadas == []                      # no baja nada al crear el índice
    assert ind.de("Entidad X", "899999-1") == [{"nit_entidad": "899999", "entidad": None}]
    assert ind.de("Entidad X", "") == [{"nit_entidad": None, "entidad": "Entidad X"}]
    assert ind.de("", "") == []
    assert llamadas == [("899999", None), (None, "Entidad X")]


def test_url_con_params():
    from agente_vacantes.navegador import url_con_params
    assert url_con_params("https://x/index", {"entidad": "5202", "f": "01/08/2026"}) == \
        "https://x/index?entidad=5202&f=01%2F08%2F2026"
    assert url_con_params("https://x/index?a=1", None) == "https://x/index?a=1"


# Fragmento RECONSTRUIDO a partir del informe de verificación de la página real
# (encabezados y textos de celdas copiados del informe; no es el HTML original completo).
HTML_LEY2013 = """
<p>Consulta Ciudadana - Declaraciones Ley 2013 de 2019</p>
<table><tr><th>Declarante</th><th>Descargar</th><th>Entidad</th><th>Cargo/Contratista</th>
<th>Tipo de publicación</th><th>Declaración No.</th><th>Fecha de publicación</th><th>Estado declaración</th></tr>
<tr><td>PERSONA UNO CEDULA DE CIUDADANIA -
                                        1000000001</td><td>Declaración Ley 2013 de 2019</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>CONTRATISTA</td><td>INGRESO</td>
<td>4189014-01 Declaración inicial</td><td>2026-11-04 12:28</td><td>FINALIZADO</td></tr>
<tr><td>PERSONA DOS CEDULA DE CIUDADANIA -
                                        1000000002</td><td>Declaración Ley 2013 de 2019 Visualizar declaración de Renta</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>VICEPRESIDENTE DE AGENCIA</td><td>RETIRO</td>
<td>4157944-01 Declaración inicial</td><td>2026-10-19 18:14</td><td>FINALIZADO</td></tr>
<tr><td>EMPRESA EJEMPLO SAS NIT-NÚMERO DE IDENTIFICACIÓN TRIBUTARIA -
                                        900000001</td><td>Declaración</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>CONTRATISTA</td><td>INGRESO</td>
<td>4108424-01 Declaración inicial</td><td>2026-09-28 09:13</td><td>FINALIZADO</td></tr>
</table>
<a href="/fdci/consultaCiudadana/index?find=FindNext&tipoPersonaId=25&entidad=5202&sort=FECHA_FINALIZACION&max=10&order=asc">Fecha</a>
<a href="/fdci/consultaCiudadana/index?find=FindNext&tipoPersonaId=25&entidad=5202&offset=10&max=10&sort=FECHA_FINALIZACION&order=desc">Siguiente</a>
"""


def test_resultados_ley2013():
    filas = sigep.parsear_resultados(HTML_LEY2013)
    assert len(filas) == 3
    f = filas[0]
    assert (f["nombre"], f["tipo_documento"], f["numero_documento"]) == (
        "PERSONA UNO", "CEDULA DE CIUDADANIA", "1000000001")
    assert f["entidad"] == "AGENCIA NACIONAL DE INFRAESTRUCTURA." and f["es_contratista"] is True
    assert f["tipo_publicacion"] == "INGRESO" and f["fecha_publicacion"] == "2026-11-04 12:28"
    assert f["numero_declaracion"].startswith("4189014") and f["estado_declaracion"] == "FINALIZADO"
    assert filas[1]["cargo"] == "VICEPRESIDENTE DE AGENCIA" and filas[1]["es_contratista"] is False
    assert filas[2]["nombre"] == "EMPRESA EJEMPLO SAS" and filas[2]["numero_documento"] == "900000001"
    assert sigep.total_resultados(HTML_LEY2013) is None  # no confundir "2019" con un total
    sig = sigep.siguiente_pagina(HTML_LEY2013)
    assert "offset=10" in sig
    assert "max=100" in sigep.con_tamano_pagina(sig, 100)


def test_ultimos_servidores_activos():
    filas = sigep.parsear_resultados(HTML_LEY2013)
    otra = dict(filas[1], tipo_publicacion="PERIÓDICO", fecha_publicacion="2025-03-01 10:00")
    activos = sigep.ultimos_servidores_activos(filas + [otra])
    assert activos == []  # su última declaración es de RETIRO; los contratistas no cuentan
