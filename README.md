# Agente de vacantes – Función Pública + SECOP II + manuales de funciones

Para cada entidad produce:

1. **Vacantes de planta con perfil**
   * **Vacantes oficiales:** cargos sin proveer según el *informe de planta de personal* que
     publica la entidad (denominación, código, grado, naturaleza, vacancia definitiva o
     temporal, dependencia y grupo). A cada uno se le une la ficha del **manual de
     funciones** (propósito y requisitos de estudio y experiencia).
   * **Movimientos posteriores:** declaraciones de **RETIRO** e **INGRESO** publicadas en la
     consulta ciudadana de la Ley 2013 de 2019 desde la fecha de corte del informe.
     *Saldo estimado = vacantes oficiales + retiros − ingresos* por denominación.
2. **Contratos que terminan:** contratos de prestación de servicios de **SECOP II** con fecha de
   fin en la ventana (por defecto 01/08/2026 – 30/11/2026), ubicados en la dependencia y con
   el nivel y la formación que se deducen del objeto.

El resultado es un Excel con las hojas *Resumen*, *1. Vacantes oficiales*, *1. Saldo por
cargo*, *1. Retiros declarados*, *2. Contratos que terminan*, *Fichas del manual* y
*Alertas*, más un JSON por entidad en `salida/entidades/`.

## Fuentes (verificadas en noviembre de 2026)

| Fuente | Qué aporta | Nota |
|---|---|---|
| `www1.funcionpublica.gov.co/fdci/consultaCiudadana/index` | Declaraciones Ley 2013: declarante, cargo, tipo (INGRESO / RETIRO / PERIÓDICO / OTRO), fecha | **No es un listado de contratos.** El filtro de fechas es la fecha de publicación de la declaración. `tipoPersonaId` 25 = natural, 26 = jurídica. El servidor envía un intermedio TLS equivocado; el agente trae el intermedio público de Let's Encrypt en `agente_vacantes/certs/` (no desactiva la verificación). |
| `www.datos.gov.co` dataset `jbjy-vk9h` (SECOP II – Contratos electrónicos) | Contratos: objeto (`descripcion_del_proceso`), fechas, valor, contratista, enlace | `nit_entidad` es numérico e incluye el dígito de verificación. |
| Sitio web de cada entidad (Transparencia → Talento humano) | Manual de funciones, informe de planta / vacantes, organigrama | No hay repositorio central: un documento por entidad. |

## Instalación

```bash
pip install -r requirements.txt
# Solo si el manual está escaneado (sin texto):
apt-get install -y tesseract-ocr tesseract-ocr-spa poppler-utils
```

La red debe permitir `www1.funcionpublica.gov.co`, `www.datos.gov.co` y el sitio de cada
entidad (por ejemplo `www.ani.gov.co`).

## Uso

```bash
# 1. Lista de entidades (≈14.800) -> entidades.csv
python -m agente_vacantes entidades

# 2. Por entidad, complete en entidades.csv (ruta o URL; varias separadas por |)
#    o deje los archivos en insumos/<codigo>/ con "manual", "planta" u "organigrama" en el nombre:
#    nit, manual, planta (informe de vacantes), organigrama, corte_planta (aaaa-mm-dd, opcional)

# 3. Ejecutar
python -m agente_vacantes ejecutar --codigo 5202          # una entidad
python -m agente_vacantes ejecutar                        # todas las de entidades.csv
```

Opciones: `--desde/--hasta` (ventana de fin de contratos), `--movimientos-desde` (por defecto,
el corte del informe de planta), `--sin-ia`, `--sin-sigep`, `--sin-secop`,
`--todos-los-tipos`, `--rehacer`. Con más de 20 entidades, SECOP II y las declaraciones se
descargan una sola vez para todas. El recorrido se reanuda donde quedó.

### Manuales escaneados (OCR)

Si junto al PDF existe un archivo `<nombre>.ocr.txt`, el agente usa ese texto. Para generarlo:

```bash
pdftoppm -r 200 -gray -png manual.pdf pg
ls pg-*.png | sort -V | OMP_THREAD_LIMIT=1 xargs -P 4 -I{} tesseract {} {} -l spa --psm 4
ls pg-*.png | sort -V | while read f; do cat "$f.txt"; done > manual.ocr.txt
```

(`OMP_THREAD_LIMIT=1` es importante: sin él los procesos compiten y el OCR va ~100 veces
más lento.) Con credenciales de Anthropic, el agente puede leer el PDF con Claude
(`claude-opus-5-5`) sin OCR.

## Limitaciones

* **El saldo estimado es una señal, no un conteo oficial.** No todos los servidores publican
  sus declaraciones a tiempo, y la declaración no dice el grado ni la dependencia. Confirme
  con la entidad o con la OPEC de la CNSC (SIMO).
* El informe de planta puede estar desactualizado (la ANI publicó el de junio de 2025); el
  agente lo marca en *Alertas*.
* Los contratos de prestación de servicios no son cargos de planta.
* La ubicación del contrato en una dependencia se deduce del texto del objeto (siglas o
  nombre); revise la columna `confianza_dependencia`.
* No se guarda el número de documento de los declarantes.

## Pruebas

```bash
python -m pytest -q
```

Las pruebas usan datos sintéticos con la estructura real de las fuentes.
