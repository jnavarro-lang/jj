# MinTIC – vacantes probables y contratos que se liberan (01/08/2026 – 30/11/2026)

* **Entidad:** MINISTERIO DE TECNOLOGIAS DE LA INFORMACION Y LAS COMUNICACIONES
* **Código SIGEP:** `0012` (tomado del `<select name="entidad">` del formulario; NIT 899999053)
* **Corrida:** 21/11/2026, `python -m agente_vacantes --sin-chrome ejecutar --codigo 0012 --sin-ia --desde 2026-08-01 --hasta 2026-11-30 --ocupacion`.
  Con `--ocupacion` tardó unos 4 minutos, así que se dejó la opción.
* **Archivos:** `vacantes_20261121_1812.xlsx` y `0012.json` (MinTIC); `futic/` (Fondo Único de
  TIC, ver la sección 3); `verificacion/` (salida de `verificar --codigo 0012`); `fuentes.md`.

## 1. Declaraciones SIGEP (Ley 2013 de 2019) publicadas en la ventana

| | Declaraciones |
|---|---|
| **Total** | **135** |
| Servidores (columna Cargo/Contratista con un cargo) | 47 (32 INGRESO, 13 RETIRO, 2 PERIÓDICO) |
| Contratistas | 88 (87 persona natural + 1 persona jurídica; 74 INGRESO, 10 PERIÓDICO, 3 OTRO, 1 RETIRO) |

Los 47 servidores son casi todos de nivel directivo y asesor: jefes de oficina, asesores,
secretario general, directores, subdirectores, ministro y viceministros. Solo 1 es
profesional especializado.

## 2. RETIROS de servidores (declaración tipo RETIRO publicada en la ventana)

Hay 13 declaraciones de retiro, que corresponden a **11 personas**: dos personas publicaron la
declaración dos veces. La fecha es la **fecha de publicación de la declaración**; el SIGEP no
trae la fecha efectiva del retiro.

| Nombre | Cargo (según SIGEP) | Fecha de publicación |
|---|---|---|
| JUAN DIEGO TORO BAUTISTA | JEFE DE OFICINA | 2026-10-02 |
| CAMILO CARRASCAL | MINISTRO | 2026-09-11 |
| LUIS EDUARDO AGUIAR DELGADILLO | DIRECTOR ADMINISTRATIVO Y/O FINANCIERO O TÉCNICO U OPERATIVO | 2026-09-07 (2 declaraciones) |
| GERMÁN ENRIQUE BACCA MEDINA | SECRETARIO GENERAL DE MINISTERIO O DE DEPARTAMENTO ADMINISTRATIVO | 2026-09-01 |
| MARIA CAROLINA ZUNIGA HERNANDEZ | ASESOR | 2026-08-28 |
| ADRIANA MARCELA DUARTE PEÑALOSA | ASESOR | 2026-08-26 |
| MARIA CAROLINA MERCADO FLOREZ | ASESOR | 2026-08-25 |
| MAGDA YOLIMA AMAYA AREVALO | SECRETARIO GENERAL DE MINISTERIO O DE DEPARTAMENTO ADMINISTRATIVO | 2026-08-19 (2 declaraciones) |
| OLGA ISABEL BUELVAS DICKSON | SECRETARIO GENERAL DE MINISTERIO O DE DEPARTAMENTO ADMINISTRATIVO | 2026-08-11 |
| GLORIA PATRICIA PERDOMO RANGEL | VICEMINISTRO | 2026-08-11 |
| YEIMI CARINA MURCIA YELA | MINISTRO | 2026-08-04 |

Todos son empleos de libre nombramiento y remoción (directivo/asesor). Que haya un retiro no
significa que el cargo siga vacante: varios ya pueden estar provistos (por ejemplo, hay 32
declaraciones de INGRESO de servidores en la misma ventana).

## 3. Contratos SECOP II que terminan en la ventana

Consulta en datos.gov.co (`jbjy-vk9h`), contratos de prestación de servicios con
`fecha_de_fin_del_contrato` entre el 01/08/2026 y el 30/11/2026:

| Entidad contratante en SECOP II | NIT | Prestación de servicios | Todos los tipos |
|---|---|---|---|
| MinTIC | 899999053 | **6** | 7 |
| Fondo Único de TIC (FUTIC) | 800131648-6 | **529** | 551 |

El MinTIC contrata casi todo a través del **Fondo Único de TIC**. En el SIGEP hay 88
contratistas declarando para la entidad 0012 en la ventana, pero en SECOP II el MinTIC solo
tiene 6 contratos. Por eso se corrió aparte el FUTIC (`--codigo 6424 --sin-sigep`, NIT
8001316486, con el manual del MinTIC solo para inferir dependencia y nivel). Los 529 contratos
del FUTIC terminan así: agosto 2, septiembre 12, octubre 371, noviembre 144. Suman
$100.951.564.753. Nivel inferido: Profesional 429, Profesional especializado 38,
Técnico/tecnólogo 29, Asistencial/apoyo 28, no determinado 5.

**La hoja "Vacantes planta" del Excel de `futic/` no tiene sentido:** el FUTIC no tiene planta
propia y esa corrida no consultó el SIGEP. Úsela solo por la hoja de contratos.

Muestra de 15 contratos: los 6 del MinTIC y 9 del FUTIC, tomados a intervalos regulares de la
lista ordenada por fecha de fin. "Dependencia inferida" y "nivel inferido" los calcula el
agente a partir del texto del objeto. "—" significa que el nombre de ninguna dependencia del
manual aparece en el objeto con confianza ≥ 90.

| Entidad | Contratista | Objeto (inicio) | Fecha fin | Valor | Dependencia inferida | Nivel inferido |
|---|---|---|---|---|---|---|
| MinTIC | Rudy Joel Nieto Henriquez | 1500464 - Prestar servicios profesionales en la formulación; estructuración y revisión técnica y metodológica para la viabilidad y aprobació… | 2026-09-30 | $97.743.000 | — | Profesional |
| MinTIC | Ana María Zapata Bedoya | 1500479. Prestar los servicios profesionales para la estructuración y formulación; de los proyectos susceptibles de ser financiados o cofin… | 2026-09-30 | $133.126.667 | — | Profesional |
| MinTIC | Alexis Peña Briceño | 1500440 Prestar servicios profesionales para acompañar y soportar técnicamente la estructuración; presentación y promoción de los proyectos … | 2026-09-30 | $144.512.500 | — | Profesional |
| MinTIC | Eva Cristina Gutiérrez Valencia | 1500438 - Prestar servicios profesionales para acompañar y soportar técnicamente la estructuración; presentación y promoción de los proyect… | 2026-09-30 | $123.702.700 | — | Profesional |
| MinTIC | Andres Fabian Cipamocha Rodriguez | 4320001 - Prestar servicios profesionales especializados al Grupo Interno de Trabajo de Gestion Pensional de la Subdireccion para la Gestion… | 2026-10-19 | $69.523.650 | Subdirección para la Gestión del Talento Humano | Profesional especializado |
| MinTIC | Paola Andrea Cardona Varón | 43300231499 - Prestar servicios profesionales especializados al Grupo Interno de Trabajo de Desarrollo del Talento Humano de la Subdirección… | 2026-11-02 | $69.523.650 | Subdirección para la Gestión del Talento Humano | Profesional especializado |
| FUTIC | Oscar Eduardo parra losada | 1500227- Prestar servicios de apoyo a la gestión para fortalecer el relacionamiento y la presencia institucional del Ministerio de Tecnologi… | 2026-08-03 | $26.485.200 | — | Técnico / tecnólogo |
| FUTIC | Leidy María Arias Tamayo | 4100002- Prestar servicios profesionales a la Oficina para la Gestión de Ingresos del Fondo; orientados al análisis económico de los proceso… | 2026-10-11 | $89.387.550 | — | Profesional |
| FUTIC | MARIA PAULA SEBA BUELVAS | 3300046 PRESTAR SERVICIOS PROFESIONALES A LA DIRECCIÓN DE ECONOMÍA DIGITAL; COMO APOYO A LA SUPERVISIÓN DESDE EL COMPONENTE JURÍDICO; EN EL … | 2026-10-13 | $69.523.650 | Subdirección para la Transformación Sectorial ⚠️ | Profesional |
| FUTIC | Camilo Andrés Torres Wilches | 3020015 - Prestar servicios profesionales especializados en temas jurídicos en el marco del despliegue de la política de seguridad digital d… | 2026-10-16 | $99.319.500 | — | Profesional especializado |
| FUTIC | Ivonne Liset Casas Alvarez | 2320009 - Prestar servicios profesionales desde el punto de vista jurídico a la Dirección de Vigilancia; Inspección y Control en el marco d… | 2026-10-22 | $69.523.650 | Subdirección de Investigaciones Administrativas | Profesional |
| FUTIC | KAREN JULIETH OTERO VILLA | 2320013 PRESTAR SERVICIOS PROFESIONALES DE CARACTER JURÍDICO A LA DIRECCIÓN DE VIGILANCIA; INSPECCIÓN Y CONTROL EN EL MARCO DEL PROCEDIMIEN… | 2026-10-25 | $79.455.600 | Subdirección de Investigaciones Administrativas | Profesional |
| FUTIC | SEBASTIAN TOVAR TORO | 4440015 - Prestar servicios profesionales para la ejecución de actividades propias del Grupo Interno de Trabajo de Gestión de Servicios Admi… | 2026-10-27 | $59.591.700 | — | Profesional |
| FUTIC | Alisson Michell Prada Tamayo | 4430022 prestar los servicios de apoyo a la gestión a través de actividades de atención al ciudadano; brindando orientación; trámite y acomp… | 2026-11-01 | $19.863.900 | — | Asistencial / apoyo a la gestión |
| FUTIC | CAMILO ANDRES ORTEGA LOPEZ | 1500134-Prestar servicios profesionales para fortalecer el relacionamiento y la presencia institucional del Ministerio de Tecnologías de la … | 2026-11-12 | $69.523.650 | — | Profesional |

⚠️ El objeto dice "Dirección de Economía Digital". El agente la asignó a una subdirección de
esa dirección porque el objeto menciona su tema. La dependencia inferida es **orientativa** y
hay que revisarla. En el FUTIC, 279 de 529 contratos quedaron sin dependencia.

## 4. Manual, planta, plazas y vacantes probables

**Documentos:** se descargó el manual vigente, el anexo de la **Resolución 03927 de 2024**
(1.249 páginas). **No** se consiguió la planta completa (Decreto 2619 de 2012 y Resolución
1351 de 2020; ver `fuentes.md`). Se usó en su lugar el **Plan de Previsión de Recursos
Humanos 2026** del MinTIC, publicado en www.mintic.gov.co, con corte al 31/12/2025.

### 4.1 Cifras oficiales del MinTIC (Plan de Previsión 2026, corte 31/12/2025)

| Nivel | Carrera | LNR | Total planta |
|---|---|---|---|
| Directivo | – | 32 | 32 |
| Asesor | 13 | 64 | 77 |
| Profesional | 400 | 20 | 420 |
| Técnico | 55 | – | 55 |
| Asistencial | 66 | 9 | 75 |
| **Total** | **534** | **125** | **659** |

* Provistos: **497** (75,3 %). Vacantes: **163** (24,7 %): **101 definitivas** y **62 temporales**.
  El propio documento anota que su planta reporta 661 empleos, frente a los 659 de los
  decretos, y que hay un trámite ante el Consejo de Estado.
* Vacantes definitivas por nivel: asistencial 11, asesor 7, directivo 8, profesional 57, técnico 18.
* Vacantes temporales por nivel: asistencial 10, profesional 45, técnico 7.
* De los empleos de libre nombramiento, 16 estaban vacantes: 8 sin proveer y 8 con encargo.

Vacantes por empleo leídas de las tablas del plan. Se recuperaron **144 de las 163 filas**: las
demás se pierden en los cortes de página del PDF, así que los totales de esta tabla son
menores que los oficiales.

| Empleo | Código | Grado | Definitivas | Temporales | Total |
|---|---|---|---|---|---|
| Director Técnico | 0100 | 23 | 2 | 0 | 2 |
| Jefe de Oficina | 0137 | 20 | 1 | 0 | 1 |
| Subdirector Técnico | 0150 | 21 | 5 | 0 | 5 |
| Asesor | 1020 | 7 / 12 / 13 / 16 / 18 | 1 / 1 / 1 / 2 / 1 | 0 | 6 |
| Profesional Especializado | 2028 | 14 | 3 | 2 | 5 |
| Profesional Especializado | 2028 | 15 | 1 | 4 | 5 |
| Profesional Especializado | 2028 | 16 | 4 | 4 | 8 |
| Profesional Especializado | 2028 | 17 | 3 | 7 | 10 |
| Profesional Especializado | 2028 | 18 | 3 | 4 | 7 |
| Profesional Especializado | 2028 | 20 | 6 | 2 | 8 |
| Profesional Especializado | 2028 | 21 | 1 | 3 | 4 |
| Profesional Especializado | 2028 | 23 | 0 | 1 | 1 |
| Profesional Especializado | 2028 | 24 | 5 | 1 | 6 |
| Profesional Especializado | 2028 | (grado no legible) | 3 | 2 | 5 |
| Profesional Universitario | 2044 | 6 | 5 | 0 | 5 |
| Profesional Universitario | 2044 | 9 | 3 | 4 | 7 |
| Profesional Universitario | 2044 | 10 | 5 | 6 | 11 |
| Profesional Universitario | 2044 | 11 | 1 | 3 | 4 |
| Técnico | 3100 | 15 / 17 | 1 / 1 | 0 | 2 |
| Técnico Administrativo | 3124 | 11 | 0 | 1 | 1 |
| Técnico Administrativo | 3124 | 13 | 8 | 1 | 9 |
| Técnico Administrativo | 3124 | (grado no legible) | 1 | 1 | 2 |
| Técnico Operativo | 3132 | 9 / 11 / 13 / 14 | 1 / 0 / 1 / 3 | 1 / 1 / 0 / 2 | 9 |
| Auxiliar Administrativo | 4044 | 11 | 1 | 1 | 2 |
| Auxiliar de Servicios Generales | 4064 | 9 | 1 | 0 | 1 |
| Conductor Mecánico | 4103 | 13 / 14 | 1 / 0 | 0 / 1 | 2 |
| Secretario Ejecutivo | 4210 | 17 | 1 | 3 | 4 |
| Secretario Ejecutivo | 4210 | 19 | 3 | 5 | 8 |
| Secretario Ejecutivo | 4210 | 24 | 1 | 0 | 1 |
| Secretario Ejecutivo del Despacho de Ministro | 4212 | 26 | 1 | 0 | 1 |
| Secretario Ejecutivo del Despacho del Viceministro | 4215 | 24 | 2 | 0 | 2 |

El corte es al 31/12/2025. El plan dice que las vacantes definitivas se ofrecerían en encargo
durante 2026 y que hay empleos en el concurso Nación 6, así que en noviembre de 2026 pueden
estar provistas. Confirme con el GIT de Administración de Personal o en SIMO.

### 4.2 Lo que calculó el agente (no usar como cifra de vacantes)

* El parser sin IA leyó 464 fichas del manual. En el MinTIC cada empleo tiene varias fichas
  (una por área funcional o perfil), cada una con su "No. de cargos". Sumadas dan 866 cargos,
  más que los 659 de la planta, así que **el manual no sirve para contar plazas**.
* Además, el agente une las fichas con la misma denominación, código y grado (84 empleos) y se
  queda con el "No. de cargos" de la primera. En el Excel salen **168 plazas, 120 ocupadas y 48
  vacantes**, cifras que **no** corresponden a la planta real.
* Ocupación según el SIGEP (`--ocupacion`): 3.470 declaraciones de la entidad (3.364 de
  personas naturales y 106 de jurídicas, de 2020 a 2026). De ahí salen **309 servidores** cuya
  última declaración no es de retiro, frente a los 497 provistos que reporta el MinTIC: el SIGEP
  no cubre a toda la planta. Hay 189 servidores que no se pudieron emparejar con un empleo del
  manual, porque el SIGEP da cargos genéricos ("PROFESIONAL ESPECIALIZADO", "ASESOR") sin
  código ni grado.

## 5. Qué no se pudo obtener o qué hay que tener en cuenta

1. **Decreto 2619 de 2012 y Resolución 1351 de 2020 (planta y su distribución):** no se
   descargaron. `normograma.mintic.gov.co` y `sidn.ramajudicial.gov.co` están bloqueados por el
   proxy de esta sesión y no se encontró el decreto en el Gestor Normativo. No hay `planta.pdf`.
2. **Google Chrome / Chromium:** el sitio del SIGEP responde **403** a cualquier navegador
   "HeadlessChrome" (su firewall bloquea esa identificación; con curl y ese User-Agent pasa lo
   mismo). No se intentó ocultar la automatización: todo se hizo con `--sin-chrome` (cliente
   HTTP con User-Agent `agente-vacantes/0.1`).
3. **Certificado de funcionpublica.gov.co:** el servidor envía una cadena incompleta (el
   certificado lo emite Let's Encrypt YR1, pero envía un intermedio de Sectigo). Para no
   desactivar la verificación TLS se agregaron a la cadena de confianza de la sesión, solo como
   intermedios, el certificado oficial **YR1** y la **ISRG Root YR firmada por ISRG Root X1**,
   tomados del repositorio `letsencrypt/website` en GitHub. La cadena se verificó con
   `openssl verify` hasta ISRG Root X1. En Windows, Chrome completa la cadena solo y no hace
   falta esto.
4. **`max=100` en la paginación del SIGEP:** la página lo ignora en la consulta con fechas
   (devuelve 10 filas por página) y el agente sigue de 10 en 10 sin problema. La consulta sin
   fechas (`--ocupacion`) devolvió todo en pocas páginas.
5. **Fecha real de retiro y fecha de fin de contrato en el SIGEP:** la página no las publica.
   Las fechas de la sección 2 son de publicación de la declaración.
6. **Dependencia del servidor:** el SIGEP no la publica, así que no se sabe de qué dependencia
   sale cada retiro.
7. **Lectura con IA (`--sin-ia`):** no se usó. El manual se leyó con el parser de texto.

## 6. Cambios hechos al agente con los datos reales (con pruebas en `tests/test_agente.py`)

* **SIGEP:** la consulta sin fechas trae 159 declaraciones de 2020 en un formato antiguo (tipo
  OTRO, sin cargo, declarante "NOMBRE CC"). Antes se contaban como **servidores activos**.
  Ahora `es_contratista` es `None` cuando no hay cargo, y esas filas no cuentan ni para la
  ocupación ni para los retiros. Con esto los servidores activos bajaron de 444 a 309. También
  se separa "CC" del nombre.
* **SIGEP:** las filas de persona JURÍDICA quedan siempre como contratistas. Antes había una
  sin cargo que contaba como servidor.
* **SIGEP:** el agente avisa si se llega al límite de 500 páginas. Antes cortaba sin avisar.
* **Manual:** si la dependencia es genérica ("Donde se ubique el cargo"), se toma la de
  "II. ÁREA FUNCIONAL". También se reconocen los títulos "lll." (con letras L). Con esto se
  pasó de 5 a 43 dependencias.
* **Dependencia del contrato:** ya no se usan nombres de una sola palabra (salía "Digital") y el
  umbral subió de 85 a 90 ("Oficina de Tecnologías de la Información" casaba con "Ministerio de
  Tecnologías de la Información…").
* **Excel:** la hoja Resumen trae una columna nueva, `servidores_sigep_ventana`.
