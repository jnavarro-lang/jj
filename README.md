# Agente de vacantes – SIGEP + SECOP II + manuales de funciones

Recorre **todas las entidades** del directorio del SIGEP y produce, por entidad:

1. **Vacantes de planta (probables):** empleos del manual de funciones / decreto de planta
   (denominación, código, grado, nivel, número de cargos, dependencia, propósito,
   funciones, requisitos de estudio y experiencia), comparados con los **servidores
   públicos** que aparecen en el SIGEP. Plazas − ocupados = vacantes probables, con su perfil.
2. **Contratos que se liberan:** contratos con fecha de finalización en la ventana
   (por defecto 01/08/2026 – 30/11/2026), tomados del SIGEP (contratistas) y de
   **SECOP II** (datos.gov.co). Para cada uno: dependencia del organigrama, nivel
   inferido (profesional, técnico, asistencial), formación mencionada en el objeto y el
   empleo del manual más parecido como perfil de referencia.

El resultado es un Excel con las hojas *Resumen*, *Vacantes planta*, *Contratos que se
liberan*, *Dependencias* y *Alertas*, más un JSON por entidad en `salida/entidades/`.

## Instalación

```bash
pip install -r requirements.txt
```

Necesita acceso a `www1.funcionpublica.gov.co` y `www.datos.gov.co`, y a los sitios web
de las entidades si los manuales se descargan por URL.

## Google Chrome

El SIGEP se consulta abriendo **Google Chrome** (Playwright con `channel="chrome"`, usa el
Chrome instalado; no hace falta `playwright install`). Se ve la ventana mientras trabaja.
`--chrome-oculto` la oculta y `--sin-chrome` usa el cliente HTTP. Si Chrome no abre, el
agente avisa y sigue con HTTP. Variables: `NAVEGADOR_RUTA` (ruta a chrome.exe),
`NAVEGADOR_VISIBLE=0`.

Por defecto el SIGEP se usa **como una persona** (`SIGEP_MODO=formulario`): para cada
entidad abre el formulario, elige *Tipo de persona*, busca y elige la entidad en *Nombre
entidad* (lista con buscador), llena las fechas, oprime **Buscar** y pasa por todas las
páginas con *Siguiente*. La lista de entidades (`python -m agente_vacantes entidades`) se
lee abriendo ese mismo campo y desplazándose hasta el final. `SIGEP_MODO=url` usa en su
lugar la URL de consulta con parámetros.

Nota: en el formulario el campo de fechas se titula *Fecha de publicación*, aunque el
parámetro se llama `fechaFinalizacionDesde/Hasta`. Hay que confirmar con `verificar` si
filtra por fecha de publicación de la declaración o por fecha de finalización.

### Verificar la página

```bash
python -m agente_vacantes verificar --codigo 5202
```

Abre el SIGEP en Chrome, lista las opciones de *Tipo de persona*, busca la entidad, hace la
consulta de la ventana por cada tipo y revisa columnas, total y paginación; también revisa
los nombres de campos de SECOP II. Deja `verificacion/informe.txt` con HTML y capturas.

En Windows: doble clic en `ejecutar_windows.bat` (opción 1 = verificar, 2 = ejecutar).

## Uso

```bash
# 1. Lista de entidades desde el formulario del SIGEP -> entidades.csv
python -m agente_vacantes entidades

# 2. Complete en entidades.csv (o deje los archivos en insumos/<codigo>/):
#    nit          -> mejora el cruce con SECOP II
#    manual       -> ruta o URL del Manual Específico de Funciones (PDF/DOCX/TXT)
#    organigrama  -> ruta o URL del organigrama (PDF o imagen)
#    planta       -> ruta o URL del decreto/resolución de planta (trae el número de cargos)

# 3. Ejecutar (todas las entidades, o solo algunas con --codigo)
python -m agente_vacantes ejecutar --desde 2026-08-01 --hasta 2026-11-30
python -m agente_vacantes ejecutar --codigo 5202
```

Opciones: `--sin-ia`, `--sin-sigep`, `--sin-secop`, `--todos-los-tipos` (todos los tipos
de contrato en SECOP, no solo prestación de servicios), `--rehacer`. El recorrido se
puede interrumpir y reanudar: las entidades que ya tienen JSON en `salida/entidades/` se
saltan.

### Lectura de manuales y organigramas

* **Con Claude** (recomendado): si hay `ANTHROPIC_API_KEY` (o un perfil de
  `ant auth login`), los PDF e imágenes se leen con el modelo `claude-opus-5-5`
  (variable `CLAUDE_MODEL`) y salida estructurada. Los PDF largos se procesan en tramos
  de 30 páginas. Está activado el reenvío automático a otro modelo si una solicitud es
  rechazada (`CLAUDE_FALLBACKS=0` para desactivarlo).
* **Sin IA** (`--sin-ia`): un parser de texto para el formato típico del manual
  (“Denominación del empleo / Código / Grado / No. de cargos…”). Es más frágil con PDF
  escaneados o tablas complejas.

### Variables de entorno

| Variable | Uso |
|---|---|
| `SIGEP_TIPO_CONTRATISTA` | `tipoPersonaId` de contratistas (por defecto 25) |
| `SIGEP_TIPO_SERVIDOR` | `tipoPersonaId` de servidores; si se deja vacío se detecta del formulario |
| `SECOP_APP_TOKEN` | token de datos.gov.co (opcional, evita límites de peticiones) |
| `PAUSA_SEG` | pausa entre peticiones (por defecto 1 s) |

## Limitaciones (léalas antes de usar los resultados)

* **“Vacante probable” no es una vacante oficial.** El directorio del SIGEP puede estar
  incompleto o desactualizado. Si una entidad no tiene servidores en el SIGEP, la columna
  *ocupacion_verificada* = NO y no se reportan vacantes. Confirme con la entidad, la
  OPEC de la CNSC (SIMO) o el decreto de planta vigente.
* El **número de cargos** casi nunca está en el manual: viene en el decreto de planta. Si
  falta, se asume 1 y se marca en *observacion*.
* No existe un repositorio central de manuales y organigramas: hay que conseguir el
  documento de cada entidad (sección de Transparencia, Ley 1712 de 2014).
* Los contratos de prestación de servicios **no** son empleos de planta. La opción 2
  muestra necesidades que se liberan, no cargos vacantes.
* El parser del SIGEP es genérico (detecta columnas por encabezado y sigue la paginación).
  Si una consulta no devuelve filas, el HTML queda en `.cache/sigep_debug/` para ajustarlo.

## Pruebas

```bash
python -m pytest -q
```

Las pruebas usan datos **sintéticos**.
