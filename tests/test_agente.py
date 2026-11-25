"""Pruebas con datos SINTÉTICOS que imitan la estructura real de las fuentes
(nombres de personas inventados)."""
from agente_vacantes import cruce, documentos, planta, sigep
from agente_vacantes.modelos import Empleo

# Estructura real de la consulta de declaraciones Ley 2013 (noviembre 2026), datos inventados
HTML = """
<form action="/fdci/consultaCiudadana/index" method="get">
<select name="tipoPersonaId" id="tipoPersonaId"><option value="26">JURÍDICA</option>
<option value="25" selected>NATURAL</option></select>
<select name="entidad" id="entidad"><option value="">(Opcional)</option>
<option value="5202" selected>AGENCIA NACIONAL DE INFRAESTRUCTURA.</option></select></form>
<table class="table"><thead><tr><th>Declarante</th><th>Descargar</th><th>Entidad</th>
<th>Cargo/Contratista</th><th>Tipo de publicación</th><th>Declaración No.</th>
<th>Fecha de publicación</th><th>Estado declaración</th></tr></thead><tbody>
<tr><td><p class="margin-bottom-5">ANA PRUEBA UNO</p><p>CEDULA DE CIUDADANIA - 1</p></td>
<td>Declaración Ley 2013 de 2019 Visualizar</td><td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td>
<td>GERENTE DE PROYECTOS O FUNCIONAL</td><td>RETIRO</td><td>1-01 Declaración inicial</td>
<td>2026-09-08 10:00</td><td>FINALIZADO</td></tr>
<tr><td><p>LUIS PRUEBA DOS</p><p>CEDULA DE CIUDADANIA - 2</p></td><td>x</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>GERENTE DE PROYECTOS O FUNCIONAL</td>
<td>INGRESO</td><td>2-01</td><td>2026-10-01 09:00</td><td>FINALIZADO</td></tr>
<tr><td><p>EVA PRUEBA TRES</p><p>CEDULA - 3</p></td><td>x</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>EXPERTO</td><td>RETIRO</td><td>3-01</td>
<td>2026-11-13 14:33</td><td>FINALIZADO</td></tr>
<tr><td><p>PEPE PRUEBA</p><p>CEDULA - 4</p></td><td>x</td>
<td>AGENCIA NACIONAL DE INFRAESTRUCTURA.</td><td>CONTRATISTA</td><td>INGRESO</td><td>4-01</td>
<td>2026-11-04 12:28</td><td>FINALIZADO</td></tr>
</tbody></table>
<ul class="pagination"><li><a class="step" href="?offset=10">2</a></li>
<li><a class="nextLink" href="/fdci/consultaCiudadana/index?find=FindNext&offset=10&max=10">Siguiente</a></li></ul>
"""

MANUAL = """
I. IDENTIFICACIÓN DEL EMPLEO
Nivel: ASESOR
Denominación del Empleo: GERENTE DE PROYECTOS O FUNCIONAL
Código: G2
Grado: 09
Número de cargos: 29
Dependencia: Despacho del Presidente de la Agencia
Cargo del Jefe Inmediato: Presidente de Agencia
II. ÁREA FUNCIONAL:
Vicepresidencia de Estructuración - PROCESO: Aeroportuario.
III. PROPÓSITO PRINCIPAL
Liderar la estructuración de proyectos aeroportuarios.
VII. REQUISITOS DE FORMACIÓN ACADÉMICA Y EXPERIENCIA
Título profesional en Ingeniería Civil y Afines. Cuarenta y nueve (49) meses de experiencia profesional relacionada.
I. IDENTIFICACIÓN DEL EMPLEO
Nivel: ASESOR
Denominación del Empleo: EXPERTO
Código: G3
Grado: 07
Número de cargos: 3
Dependencia: Despacho del Presidente de la Agencia
II. ÁREA FUNCIONAL:
Vicepresidencia Jurídica
III. PROPÓSITO PRINCIPAL
Asesorar jurídicamente.
"""

OFICIALES = [
    {"naturaleza": "Libre Nombramiento", "vacancia": "Vacancia definitiva",
     "denominacion": "Gerente de Proyectos o Funcional", "codigo": "G2", "grado": "09",
     "dependencia": "Vicepresidencia de Estructuración", "grupo": "VES - Aeropuertos"},
]


def test_parser_declaraciones():
    assert [o.valor for o in sigep.opciones_select(HTML, "tipoPersonaId")] == ["26", "25"]
    filas = sigep.parsear_declaraciones(HTML)
    assert len(filas) == 4
    assert filas[0] == {"nombre": "ANA PRUEBA UNO", "entidad": "AGENCIA NACIONAL DE INFRAESTRUCTURA.",
                        "cargo": "GERENTE DE PROYECTOS O FUNCIONAL", "tipo": "RETIRO",
                        "declaracion": "1-01 Declaración inicial", "fecha": "2026-09-08 10:00",
                        "estado": "FINALIZADO"}
    assert all("CEDULA" not in v for f in filas for v in f.values())  # no se guarda el documento
    assert sigep.hay_siguiente(HTML)


def test_manual_heuristico_codigos_con_letra():
    empleos = documentos.empleos_heuristico(MANUAL)
    assert [(e.denominacion, e.codigo, e.grado, e.numero_cargos) for e in empleos] == [
        ("GERENTE DE PROYECTOS O FUNCIONAL", "G2", "09", 29), ("EXPERTO", "G3", "07", 3)]
    assert empleos[0].area_funcional.startswith("Vicepresidencia de Estructuración")
    assert "Ingeniería Civil" in empleos[0].requisitos_estudio


def test_separar_denominacion():
    assert planta.separar_denominacion("Gerente de Proyectos o Funcional,\nCódigo G2, Grado 09") == \
        ("Gerente de Proyectos o Funcional", "G2", "09")
    assert planta.separar_denominacion("Técnico Asistencial, Código O1, Grado 04") == \
        ("Técnico Asistencial", "O1", "04")


def test_vacantes_planta():
    empleos = documentos.empleos_heuristico(MANUAL)
    decl = sigep.parsear_declaraciones(HTML)
    detalle, balance, retiros = cruce.vacantes_planta(OFICIALES, decl, empleos)
    assert detalle[0]["ficha_manual"].startswith("GERENTE DE PROYECTOS O FUNCIONAL G2-09")
    assert "Ingeniería Civil" in detalle[0]["requisitos"]
    b = {x["denominacion"]: x for x in balance}
    # 1 oficial + 1 retiro - 1 ingreso = 1 ; experto: 0 + 1 - 0 = 1 ; contratistas excluidos
    assert b["Gerente De Proyectos O Funcional"]["saldo_estimado"] == 1
    assert b["Experto"]["saldo_estimado"] == 1
    assert "Contratista" not in b
    assert [(r["cargo"], r["ingresos_posteriores_mismo_cargo"]) for r in retiros] == [
        ("EXPERTO", 0), ("GERENTE DE PROYECTOS O FUNCIONAL", 1)]


def test_perfil_respeta_grado():
    empleos = [Empleo(denominacion="EXPERTO", codigo="G3", grado="07")]
    assert cruce.perfil_para("Experto", "G3", "08", "", empleos) is None
    assert cruce.perfil_para("Experto", "G3", "07", "", empleos) is not None


def test_contratos_que_se_liberan():
    deps = ["Secretaría de Hacienda", "Secretaría de Salud"]
    contratos = [
        {"fuente": "SECOP II", "contratista": "PEDRO", "fecha_fin": "2026-10-31",
         "objeto": "Prestación de servicios profesionales como abogado para la Secretaría de Salud"},
        {"fuente": "SECOP II", "contratista": "PEDRO", "fecha_fin": "2026-10-31", "objeto": "duplicado"},
    ]
    filas = cruce.contratos_que_se_liberan(contratos, deps, [])
    assert len(filas) == 1
    assert filas[0]["dependencia"] == "Secretaría de Salud"
    assert filas[0]["nivel_inferido"] == "Profesional" and "abogad" in filas[0]["formacion_mencionada"]


def test_siglas_y_cargos_parecidos():
    assert cruce.siglas_de(OFICIALES) == {"VES": "Vicepresidencia de Estructuración"}
    dep, conf = cruce.ubicar_dependencia("apoyo a la VES en aeropuertos", [], {"VES": "Vicepresidencia de Estructuración"})
    assert (dep, conf) == ("Vicepresidencia de Estructuración", 70)
    assert not cruce._mismo_empleo("PRESIDENTE DE AGENCIA", "VICEPRESIDENTE DE AGENCIA")
    assert cruce._mismo_empleo("Técnico Asistencial", "TECNICO ASISTENCIAL")
