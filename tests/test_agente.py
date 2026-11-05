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
